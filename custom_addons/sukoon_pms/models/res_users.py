from odoo import api, models

DASHBOARD_XMLID = 'sukoon_pms.action_sukoon_dashboard'
USER_GROUP_XMLID = 'sukoon_pms.group_sukoon_user'


class ResUsers(models.Model):
    """Land Sukoon users on the Sukoon dashboard after they log in.

    Only fills an empty Home Action: anyone who has picked their own
    landing page (Preferences, or Settings > Users) keeps it.
    """
    _inherit = 'res.users'

    def _sukoon_fill_home_action(self):
        action = self.env.ref(DASHBOARD_XMLID, raise_if_not_found=False)
        group = self.env.ref(USER_GROUP_XMLID, raise_if_not_found=False)
        if not (action and group):
            return
        targets = self.filtered(
            lambda u: not u.action_id and not u.share and group in u.all_group_ids)
        if targets:
            targets.sudo().write({'action_id': action.id})

    @api.model
    def _sukoon_set_home_action(self):
        """Called from data on every install/upgrade for existing users."""
        group = self.env.ref(USER_GROUP_XMLID, raise_if_not_found=False)
        if not group:
            return
        self.with_context(active_test=False).search([
            ('all_group_ids', 'in', group.ids),
            ('action_id', '=', False),
        ])._sukoon_fill_home_action()

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sukoon_fill_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'group_ids' in vals:
            self._sukoon_fill_home_action()
        return res
