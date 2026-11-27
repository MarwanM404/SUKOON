from datetime import timedelta

from odoo import api, fields, models


def _month_start(env):
    return fields.Date.context_today(env['res.users']).replace(day=1)


def _month_end(env):
    start = _month_start(env)
    return (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)


class SukoonOwnerStatement(models.TransientModel):
    """Bookings minus commission minus expenses for one owner and period.

    A booking counts in the period its check-in falls in, the same rule the
    dashboard uses. Cancelled bookings are left out.
    """
    _name = 'sukoon.owner.statement'
    _description = 'Owner Statement'

    owner_id = fields.Many2one(
        'res.partner', string='Owner', required=True,
        domain=[('is_property_owner', '=', True)])
    date_from = fields.Date(
        string='From', required=True, default=lambda self: _month_start(self.env))
    date_to = fields.Date(
        string='To', required=True, default=lambda self: _month_end(self.env))
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    reservation_ids = fields.Many2many(
        'sukoon.reservation', compute='_compute_statement', string='Booking Lines')
    expense_ids = fields.Many2many(
        'sukoon.expense', compute='_compute_statement', string='Expense Lines')
    booking_count = fields.Integer(compute='_compute_statement')
    expense_count = fields.Integer(compute='_compute_statement')
    gross = fields.Monetary(string='Bookings', compute='_compute_statement')
    commission = fields.Monetary(
        string='Management Commission', compute='_compute_statement')
    expense_total = fields.Monetary(string='Expenses', compute='_compute_statement')
    net_payout = fields.Monetary(string='Net Payout', compute='_compute_statement')

    @api.depends('owner_id')
    def _compute_display_name(self):
        for st in self:
            st.display_name = (
                self.env._('Statement: %s', st.owner_id.name) if st.owner_id
                else self.env._('Owner Statement'))

    @api.depends('owner_id', 'date_from', 'date_to')
    def _compute_statement(self):
        Reservation = self.env['sukoon.reservation']
        Expense = self.env['sukoon.expense']
        for st in self:
            if not (st.owner_id and st.date_from and st.date_to):
                reservations, expenses = Reservation, Expense
            else:
                reservations = Reservation.search([
                    ('owner_id', '=', st.owner_id.id),
                    ('state', '!=', 'cancelled'),
                    ('check_in', '>=', st.date_from),
                    ('check_in', '<=', st.date_to),
                ], order='check_in asc')
                expenses = Expense.search([
                    ('owner_id', '=', st.owner_id.id),
                    ('date', '>=', st.date_from),
                    ('date', '<=', st.date_to),
                ], order='date asc')
            st.reservation_ids = reservations
            st.expense_ids = expenses
            st.booking_count = len(reservations)
            st.expense_count = len(expenses)
            st.gross = sum(reservations.mapped('total_amount'))
            st.commission = sum(reservations.mapped('commission_amount'))
            st.expense_total = sum(expenses.mapped('amount'))
            st.net_payout = st.gross - st.commission - st.expense_total
