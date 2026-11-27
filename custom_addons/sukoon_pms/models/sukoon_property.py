from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SukoonProperty(models.Model):
    """A rental unit managed on behalf of its owner."""
    _name = 'sukoon.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Property Name', required=True, tracking=True)
    address = fields.Char(string='Address')
    owner_id = fields.Many2one(
        'res.partner', string='Owner', required=True, tracking=True, index=True,
        domain=[('is_property_owner', '=', True)])
    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    nightly_rate = fields.Monetary(string='Base Nightly Rate', tracking=True)
    commission_pct = fields.Float(
        string='Management Commission (%)', default=20.0, tracking=True,
        help='Share of each booking kept as the management fee. New '
             'reservations copy this value, so changing it later does not '
             'rewrite past bookings.')
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()

    reservation_ids = fields.One2many('sukoon.reservation', 'property_id')
    task_ids = fields.One2many('sukoon.task', 'property_id')
    reservation_count = fields.Integer(compute='_compute_counts')
    open_task_count = fields.Integer(compute='_compute_counts')

    @api.depends('reservation_ids', 'task_ids.state')
    def _compute_counts(self):
        for prop in self:
            prop.reservation_count = len(prop.reservation_ids)
            prop.open_task_count = len(
                prop.task_ids.filtered(lambda t: t.state != 'done'))

    @api.constrains('commission_pct')
    def _check_commission_pct(self):
        for prop in self:
            if not 0 <= prop.commission_pct <= 100:
                raise ValidationError(
                    self.env._('Commission must be between 0 and 100 percent.'))

    def action_view_reservations(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sukoon_pms.action_sukoon_reservation')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action

    def action_view_open_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sukoon_pms.action_sukoon_task')
        action['domain'] = [('property_id', '=', self.id), ('state', '!=', 'done')]
        action['context'] = {'default_property_id': self.id}
        return action
