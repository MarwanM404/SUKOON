from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSukoon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls.env['res.partner'].create({
            'name': 'Test Owner', 'is_property_owner': True})
        cls.other_owner = cls.env['res.partner'].create({
            'name': 'Other Owner', 'is_property_owner': True})
        cls.prop = cls.env['sukoon.property'].create({
            'name': 'Test Villa', 'owner_id': cls.owner.id,
            'nightly_rate': 200, 'commission_pct': 20})
        cls.other_prop = cls.env['sukoon.property'].create({
            'name': 'Other Flat', 'owner_id': cls.other_owner.id,
            'commission_pct': 10})

    def _res(self, start, end, prop=None, **vals):
        return self.env['sukoon.reservation'].create({
            'property_id': (prop or self.prop).id,
            'guest_name': 'Guest',
            'check_in': start,
            'check_out': end,
            **vals,
        })

    def test_amounts_and_reference(self):
        res = self._res(date(2026, 3, 1), date(2026, 3, 5), total_amount=1000)
        self.assertEqual(res.nights, 4)
        self.assertEqual(res.commission_pct, 20)
        self.assertAlmostEqual(res.commission_amount, 200)
        self.assertAlmostEqual(res.owner_payout, 800)
        self.assertEqual(res.owner_id, self.owner)
        self.assertTrue(res.name.startswith('RES/'))

    def test_commission_is_snapshotted(self):
        res = self._res(date(2026, 3, 1), date(2026, 3, 5), total_amount=1000)
        self.prop.commission_pct = 30
        self.assertEqual(res.commission_pct, 20,
                         'Changing the property rate must not rewrite past bookings')
        new = self._res(date(2026, 3, 5), date(2026, 3, 7), total_amount=100)
        self.assertEqual(new.commission_pct, 30)

    def test_checkout_must_follow_checkin(self):
        with self.assertRaises(ValidationError):
            self._res(date(2026, 3, 5), date(2026, 3, 5))

    def test_no_double_booking(self):
        self._res(date(2026, 4, 1), date(2026, 4, 5))
        with self.assertRaises(ValidationError):
            self._res(date(2026, 4, 4), date(2026, 4, 8))
        # Check-out day can be the next guest's check-in day.
        self._res(date(2026, 4, 5), date(2026, 4, 7))
        # Another property is unaffected.
        self._res(date(2026, 4, 2), date(2026, 4, 4), prop=self.other_prop)

    def test_cancelled_bookings_free_the_dates(self):
        first = self._res(date(2026, 5, 1), date(2026, 5, 5))
        first.action_cancel()
        self._res(date(2026, 5, 2), date(2026, 5, 4))
        # Reopening the cancelled one would now clash.
        with self.assertRaises(ValidationError):
            first.action_reset_upcoming()

    def test_status_flow(self):
        res = self._res(date(2026, 6, 1), date(2026, 6, 3))
        self.assertEqual(res.state, 'upcoming')
        with self.assertRaises(UserError):
            res.action_check_out()
        res.action_check_in()
        self.assertEqual(res.state, 'in_stay')
        res.action_check_out()
        self.assertEqual(res.state, 'completed')
        with self.assertRaises(UserError):
            res.action_cancel()

    def test_owner_statement(self):
        self._res(date(2026, 7, 2), date(2026, 7, 6), total_amount=1000)       # counts
        self._res(date(2026, 7, 10), date(2026, 7, 12), total_amount=500,
                  state='cancelled')                                          # cancelled
        self._res(date(2026, 8, 1), date(2026, 8, 3), total_amount=400)       # next month
        self._res(date(2026, 7, 3), date(2026, 7, 5), prop=self.other_prop,
                  total_amount=999)                                           # other owner
        self.env['sukoon.expense'].create({
            'name': 'Plumber', 'property_id': self.prop.id,
            'amount': 150, 'date': date(2026, 7, 15)})
        self.env['sukoon.expense'].create({
            'name': 'June bill', 'property_id': self.prop.id,
            'amount': 70, 'date': date(2026, 6, 30)})
        st = self.env['sukoon.owner.statement'].create({
            'owner_id': self.owner.id,
            'date_from': date(2026, 7, 1), 'date_to': date(2026, 7, 31)})
        self.assertEqual(st.booking_count, 1)
        self.assertEqual(st.expense_count, 1)
        self.assertAlmostEqual(st.gross, 1000)
        self.assertAlmostEqual(st.commission, 200)
        self.assertAlmostEqual(st.expense_total, 150)
        self.assertAlmostEqual(st.net_payout, 650)

    def test_dashboard_data(self):
        data = self.env['sukoon.reservation'].get_dashboard_data()
        for key in ('kpis', 'statement', 'arrivals', 'departures', 'open_tasks', 'domains'):
            self.assertIn(key, data)
        self.assertGreaterEqual(data['kpis']['active_properties'], 2)

    def test_home_action_for_sukoon_users(self):
        dashboard = self.env.ref('sukoon_pms.action_sukoon_dashboard')
        sukoon_group = self.env.ref('sukoon_pms.group_sukoon_user')
        internal = self.env.ref('base.group_user')
        Users = self.env['res.users'].with_context(no_reset_password=True)

        staff = Users.create({'name': 'Staff', 'login': 'sukoon_staff',
                              'group_ids': [(6, 0, [sukoon_group.id])]})
        self.assertEqual(staff.action_id.id, dashboard.id)

        other = Users.create({'name': 'Other', 'login': 'sukoon_other',
                              'group_ids': [(6, 0, [internal.id])]})
        self.assertFalse(other.action_id, 'Non-Sukoon users keep the default landing page')
        other.write({'group_ids': [(4, sukoon_group.id)]})
        self.assertEqual(other.action_id.id, dashboard.id, 'Joining Sukoon sets the dashboard')

        chosen = self.env.ref('sukoon_pms.action_sukoon_reservation')
        picky = Users.create({'name': 'Picky', 'login': 'sukoon_picky',
                              'action_id': chosen.id,
                              'group_ids': [(6, 0, [sukoon_group.id])]})
        self.assertEqual(picky.action_id.id, chosen.id, 'A chosen home action is never overwritten')

        self.assertEqual(self.env.ref("base.user_admin").action_id.id, dashboard.id)

    def test_counts_on_property_and_owner(self):
        self._res(date(2026, 9, 1), date(2026, 9, 3))
        self.env['sukoon.task'].create({
            'name': 'Clean', 'property_id': self.prop.id, 'due_date': date(2026, 9, 3)})
        self.env['sukoon.task'].create({
            'name': 'Done job', 'property_id': self.prop.id,
            'due_date': date(2026, 9, 1), 'state': 'done'})
        self.assertEqual(self.prop.reservation_count, 1)
        self.assertEqual(self.prop.open_task_count, 1)
        self.assertEqual(self.owner.sukoon_property_count, 1)
