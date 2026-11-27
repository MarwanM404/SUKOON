from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_amount, format_date


class SukoonReservation(models.Model):
    """A booking of one property for a date range."""
    _name = 'sukoon.reservation'
    _description = 'Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'state_sequence, check_in desc, id desc'
    _rec_names_search = ['name', 'guest_name']

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: self.env._('New'))
    property_id = fields.Many2one(
        'sukoon.property', string='Property', required=True, tracking=True,
        index=True)
    owner_id = fields.Many2one(
        related='property_id.owner_id', store=True, string='Owner')
    guest_name = fields.Char(string='Guest Name', required=True, tracking=True)
    check_in = fields.Date(string='Check-in', required=True, tracking=True)
    check_out = fields.Date(string='Check-out', required=True, tracking=True)
    nights = fields.Integer(compute='_compute_nights', store=True)
    currency_id = fields.Many2one(related='property_id.currency_id')
    total_amount = fields.Monetary(string='Booking Value', tracking=True)
    commission_pct = fields.Float(
        string='Commission (%)', compute='_compute_commission_pct',
        store=True, readonly=False, precompute=True,
        help="Copied from the property when the booking is made.")
    commission_amount = fields.Monetary(
        string='Commission', compute='_compute_amounts', store=True)
    owner_payout = fields.Monetary(
        string='Owner Payout', compute='_compute_amounts', store=True)
    state = fields.Selection(
        [('upcoming', 'Upcoming'),
         ('in_stay', 'In stay'),
         ('completed', 'Completed'),
         ('cancelled', 'Cancelled')],
        string='Status', compute='_compute_state', store=True, readonly=False,
        precompute=True, required=True, tracking=True, index=True,
        group_expand=True,
        help="Follows the dates: Upcoming before check-in, In stay from the "
             "check-in day, Completed from the check-out day. Only Cancelled "
             "is set by hand.")
    state_sequence = fields.Integer(
        compute='_compute_state_sequence', store=True, index=True)
    notes = fields.Text()

    # ------------------------------------------------------------------
    # Computes and constraints
    # ------------------------------------------------------------------

    def _state_for_dates(self, today):
        """The status the dates call for on `today` (ignores cancellation)."""
        self.ensure_one()
        if not self.check_in or today < self.check_in:
            return 'upcoming'
        if self.check_out and today >= self.check_out:
            return 'completed'
        return 'in_stay'

    @api.depends('check_in', 'check_out')
    def _compute_state(self):
        # Runs when the dates change; the daily cron handles the passing of
        # time. A cancelled booking stays cancelled until it is reopened.
        today = fields.Date.context_today(self)
        for res in self:
            res.state = ('cancelled' if res.state == 'cancelled'
                         else res._state_for_dates(today))

    @api.depends('state')
    def _compute_state_sequence(self):
        order = [value for value, _label in self._fields['state'].selection]
        for res in self:
            res.state_sequence = order.index(res.state) if res.state in order else len(order)

    @api.depends('guest_name', 'name')
    def _compute_display_name(self):
        # Guest first, so calendar bars and breadcrumbs read naturally.
        for res in self:
            res.display_name = (
                '%s (%s)' % (res.guest_name, res.name) if res.guest_name else res.name)

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for res in self:
            if res.check_in and res.check_out:
                res.nights = max((res.check_out - res.check_in).days, 0)
            else:
                res.nights = 0

    @api.depends('property_id')
    def _compute_commission_pct(self):
        # Only depends on the property link, not on the property's rate,
        # so later commission changes do not rewrite past bookings.
        for res in self:
            res.commission_pct = res.property_id.commission_pct

    @api.depends('total_amount', 'commission_pct')
    def _compute_amounts(self):
        for res in self:
            res.commission_amount = res.total_amount * res.commission_pct / 100.0
            res.owner_payout = res.total_amount - res.commission_amount

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for res in self:
            if res.check_in and res.check_out and res.check_out <= res.check_in:
                raise ValidationError(
                    self.env._('Check-out must be after check-in.'))

    @api.constrains('property_id', 'check_in', 'check_out', 'state')
    def _check_no_double_booking(self):
        for res in self.filtered(lambda r: r.state != 'cancelled'):
            clash = self.search([
                ('id', '!=', res.id),
                ('property_id', '=', res.property_id.id),
                ('state', '!=', 'cancelled'),
                ('check_in', '<', res.check_out),
                ('check_out', '>', res.check_in),
            ], limit=1)
            if clash:
                raise ValidationError(self.env._(
                    '%(property)s is already booked from %(start)s to %(end)s '
                    '(%(ref)s, %(guest)s).',
                    property=res.property_id.name,
                    start=format_date(self.env, clash.check_in),
                    end=format_date(self.env, clash.check_out),
                    ref=clash.name, guest=clash.guest_name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = (self.env['ir.sequence'].next_by_code('sukoon.reservation')
                                or self.env._('New'))
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Status: cancel / reopen by hand, everything else from the dates
    # ------------------------------------------------------------------

    def _check_state_in(self, allowed):
        for res in self:
            if res.state not in allowed:
                raise UserError(self.env._(
                    '%(ref)s is %(state)s and cannot be changed that way.',
                    ref=res.name,
                    state=dict(self._fields['state'].selection)[res.state]))

    def action_cancel(self):
        self._check_state_in(['upcoming', 'in_stay'])
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        """Undo a cancellation; the status goes back to what the dates say."""
        self._check_state_in(['cancelled'])
        today = fields.Date.context_today(self)
        for res in self:
            res.state = res._state_for_dates(today)

    @api.model
    def _cron_update_states(self):
        """Daily: move bookings along as their check-in/check-out days arrive.

        Also run on every module install/upgrade, so a server that was off
        overnight catches up straight away.
        """
        today = fields.Date.context_today(self)
        moves = {}
        for res in self.search([('state', 'in', ('upcoming', 'in_stay'))]):
            new_state = res._state_for_dates(today)
            if new_state != res.state:
                moves.setdefault(new_state, self.browse())
                moves[new_state] |= res
        for new_state, records in moves.items():
            records.write({'state': new_state})

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @api.model
    def get_dashboard_data(self):
        """Everything the dashboard shows, in one call."""
        today = fields.Date.context_today(self)
        in_7 = today + timedelta(days=7)
        month_start = today.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        currency = self.env.company.currency_id
        state_labels = dict(self._fields['state'].selection)
        Task = self.env['sukoon.task']

        def money(amount):
            return format_amount(self.env, amount, currency)

        def res_rows(records, date_field):
            return [{
                'id': r.id,
                'title': r.guest_name,
                'sub': '%s · %s' % (r.property_id.name, format_date(self.env, r[date_field])),
                'state': r.state,
                'state_label': state_labels[r.state],
            } for r in records[:6]]

        # Dates as strings so the domains can be handed to the web client.
        d_today, d_in_7 = fields.Date.to_string(today), fields.Date.to_string(in_7)
        d_month, d_next = fields.Date.to_string(month_start), fields.Date.to_string(next_month)
        live = [('state', '!=', 'cancelled')]
        arrivals_domain = live + [('check_in', '>=', d_today), ('check_in', '<=', d_in_7)]
        departures_domain = live + [('check_out', '>=', d_today), ('check_out', '<=', d_in_7)]
        arrivals = self.search(arrivals_domain, order='check_in asc')
        departures = self.search(departures_domain, order='check_out asc')

        open_tasks_domain = [('state', '!=', 'done')]
        open_tasks = Task.search(open_tasks_domain, order='due_date asc')
        task_labels = dict(Task._fields['state'].selection)

        month_domain = live + [('check_in', '>=', d_month), ('check_in', '<', d_next)]
        month_res = self.search(month_domain)
        gross = sum(month_res.mapped('total_amount'))
        commission = sum(month_res.mapped('commission_amount'))
        month_exp = self.env['sukoon.expense'].search(
            [('date', '>=', d_month), ('date', '<', d_next)])
        expenses = sum(month_exp.mapped('amount'))

        return {
            'month_label': format_date(self.env, today, date_format='MMMM y'),
            'kpis': {
                'active_properties': self.env['sukoon.property'].search_count([]),
                'arrivals': len(arrivals),
                'departures': len(departures),
                'open_tasks': len(open_tasks),
                'revenue': money(gross),
                'owed_to_owners': money(gross - commission - expenses),
            },
            'statement': {
                'gross': money(gross),
                'commission': money(commission),
                'expenses': money(expenses),
                'net': money(gross - commission - expenses),
            },
            'arrivals': res_rows(arrivals, 'check_in'),
            'departures': res_rows(departures, 'check_out'),
            'open_tasks': [{
                'id': t.id,
                'title': t.name,
                'sub': '%s · due %s' % (t.property_id.name, format_date(self.env, t.due_date)),
                'state': t.state,
                'state_label': task_labels[t.state],
            } for t in open_tasks[:6]],
            'domains': {
                'arrivals': arrivals_domain,
                'departures': departures_domain,
                'open_tasks': open_tasks_domain,
                'month': month_domain,
            },
        }
