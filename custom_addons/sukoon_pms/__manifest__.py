{
    'name': 'Sukoon PMS',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Simple vacation-rental management: owners, properties, '
               'reservations, cleaning tasks, expenses and owner statements.',
    'description': """
Sukoon PMS
==========
A deliberately small property management system for teams that manage
short-term rental units on behalf of their owners.

* Owners and the properties they own, each with a management commission
* Reservations with four statuses: Upcoming, In stay, Completed, Cancelled
* Cleaning, maintenance, inspection and restock tasks
* Expenses per property
* Monthly owner statements: bookings - commission - expenses = net payout
* A dashboard with this week's arrivals, departures, open tasks and
  this month's numbers
""",
    'author': 'Marwan Morad',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/sukoon_security.xml',
        'security/ir.model.access.csv',
        'data/sukoon_sequence.xml',
        'data/sukoon_cron.xml',
        'views/sukoon_property_views.xml',
        'views/sukoon_owner_views.xml',
        'views/sukoon_reservation_views.xml',
        'views/sukoon_task_views.xml',
        'views/sukoon_expense_views.xml',
        'wizard/sukoon_owner_statement_views.xml',
        'views/sukoon_dashboard_action.xml',
        'views/sukoon_menus.xml',
        'data/sukoon_home_action.xml',
    ],
    'demo': [
        'demo/sukoon_demo.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'sukoon_pms/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_backend': [
            'sukoon_pms/static/src/dashboard/**/*',
        ],
    },
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
}
