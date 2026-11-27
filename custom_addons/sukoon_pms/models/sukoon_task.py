from odoo import fields, models


class SukoonTask(models.Model):
    """Turnover cleans, maintenance jobs, inspections and restocks."""
    _name = 'sukoon.task'
    _description = 'Cleaning & Maintenance Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date asc, id'

    name = fields.Char(string='Task', required=True, tracking=True)
    property_id = fields.Many2one(
        'sukoon.property', string='Property', required=True, index=True,
        tracking=True)
    reservation_id = fields.Many2one(
        'sukoon.reservation', string='Reservation',
        domain="[('property_id', '=', property_id)]",
        help='Optional: the stay this task is for, e.g. a turnover clean.')
    task_type = fields.Selection(
        [('cleaning', 'Cleaning'),
         ('maintenance', 'Maintenance'),
         ('inspection', 'Inspection'),
         ('restock', 'Restock')],
        string='Type', default='cleaning', required=True)
    due_date = fields.Date(
        string='Due Date', required=True, default=fields.Date.context_today,
        tracking=True)
    assignee = fields.Char(string='Assigned To', tracking=True)
    state = fields.Selection(
        [('pending', 'Pending'),
         ('in_progress', 'In progress'),
         ('done', 'Done')],
        string='Status', default='pending', required=True, tracking=True,
        group_expand=True)
    notes = fields.Text()

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
