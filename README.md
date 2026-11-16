# Equipment Checkout

A web prototype for an FIU departmental equipment desk: Staff check items in and out, Students
see what is available. Built with Python, Django, PostgreSQL and Bootstrap (server-rendered pages).

| Doc | Read it to |
| --- | --- |
| [docs/SETUP.md](docs/SETUP.md) | Get the project running on your Mac in PyCharm (free edition is fine) |
| [docs/TEAM_GUIDE.md](docs/TEAM_GUIDE.md) | See how the code is laid out, where your story goes, and the Git and database routine |
| [docs/US-01.md](docs/US-01.md) | See what US-01 does and which test proves each acceptance criterion |

## Where things are

```
equipment-checkout/
├── manage.py                 command runner: runserver, migrate, seed_demo, ...
├── pytest.ini                tells pytest which Django settings to use
├── requirements.txt          packages to install
├── config/                   site-wide settings and the top-level URL list
├── inventory/                the app
│   ├── models.py             Asset, Profile, RosterImport, Loan, LoanEvent
│   ├── services.py           LoanService and AccountService: every multi-table write
│   ├── permissions.py        @staff_required, @admin_required (Groups: Student, Staff, Admin)
│   ├── admin.py              US-07 Admin inventory in the Django admin site
│   ├── forms.py              catalog filters, desk forms, account forms
│   ├── urls.py               this app's URLs, one section per story
│   ├── views/                one file per story
│   ├── templates/            one page per view
│   ├── fixtures/             assets.json (15 items), mock_roster.csv (6 students)
│   ├── management/commands/  seed_demo: demo inventory, logins, roster, loans
│   ├── migrations/           saved table changes; commit these
│   └── tests/                one test file per story, one test per acceptance criterion
└── docs/                     setup, team guide, one note per story (US-01.md ... US-09.md)
```

## Story status

| Story | Status | Notes |
| --- | --- | --- |
| US-01 Public catalog | Done | [docs/US-01.md](docs/US-01.md) |
| US-02 Semester roster import | Done | [docs/US-02.md](docs/US-02.md) |
| US-03 Walk-up checkout | Done | [docs/US-03.md](docs/US-03.md) |
| US-04 Return and damage note | Done | [docs/US-04.md](docs/US-04.md) |
| US-05 Student's own loans | Done | [docs/US-05.md](docs/US-05.md) |
| US-06 Overdue list and event log | Done | [docs/US-06.md](docs/US-06.md) |
| US-07 Admin inventory and seed data | Done | [docs/US-07.md](docs/US-07.md) |
| US-08 Activation and sign-in | Done | [docs/US-08.md](docs/US-08.md) |
| US-09 Staff accounts and roles | Done | [docs/US-09.md](docs/US-09.md) |
