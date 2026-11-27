from odoo import api, fields, models


class ResPartner(models.Model):
    """Owners are ordinary contacts flagged as property owners."""
    _inherit = 'res.partner'

    is_property_owner = fields.Boolean(string='Property Owner')
    payout_notes = fields.Text(
        string='Payout Notes',
        help='How and when this owner is paid, e.g. bank transfer monthly on the 5th.',
    )
    sukoon_property_ids = fields.One2many(
        'sukoon.property', 'owner_id', string='Owned Properties')
    sukoon_property_count = fields.Integer(
        string='Rental Properties', compute='_compute_sukoon_property_count')

    @api.depends('sukoon_property_ids')
    def _compute_sukoon_property_count(self):
        for partner in self:
            partner.sukoon_property_count = len(partner.sukoon_property_ids)

    def action_view_sukoon_properties(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sukoon_pms.action_sukoon_property')
        action['domain'] = [('owner_id', '=', self.id)]
        action['context'] = {'default_owner_id': self.id}
        return action

    def action_open_owner_statement(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sukoon_pms.action_sukoon_owner_statement')
        action['context'] = {'default_owner_id': self.id}
        return action
