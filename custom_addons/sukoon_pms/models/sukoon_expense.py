from odoo import fields, models


class SukoonExpense(models.Model):
    """A cost charged against a property, deducted on the owner statement."""
    _name = 'sukoon.expense'
    _description = 'Property Expense'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True, tracking=True)
    property_id = fields.Many2one(
        'sukoon.property', string='Property', required=True, index=True,
        tracking=True)
    owner_id = fields.Many2one(
        related='property_id.owner_id', store=True, string='Owner')
    currency_id = fields.Many2one(related='property_id.currency_id')
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today,
        tracking=True)
    category = fields.Selection(
        [('cleaning', 'Cleaning'),
         ('maintenance', 'Maintenance'),
         ('supplies', 'Supplies'),
         ('utilities', 'Utilities'),
         ('fees', 'Fees'),
         ('other', 'Other')],
        string='Category', default='maintenance', required=True)
    notes = fields.Text()