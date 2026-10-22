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
├── manage.py                 command runner: runserver, migrate, loaddata, ...
├── pytest.ini                tells pytest which Django settings to use
├── requirements.txt          packages to install
├── config/                   site-wide settings and the top-level URL list
│   ├── settings.py           database connection, installed apps
│   └── urls.py               / -> catalog, /admin/, /accounts/ (sign-in)
├── inventory/                the app: everything about equipment
│   ├── models.py             database tables (Asset)
│   ├── migrations/           saved table changes; commit these
│   ├── fixtures/assets.json  15 demo items
│   ├── forms.py              catalog filter boxes
│   ├── permissions.py        @staff_required (Students get 403)
│   ├── urls.py               this app's URLs, one section per story
│   ├── views/                one file per story
│   │   ├── catalog.py        US-01 catalog page
│   │   └── checkout.py       US-03 placeholder (Staff only)
│   ├── templates/            HTML: base.html, catalog.html, sign-in page
│   ├── management/commands/  seed_demo_users: temporary demo logins
│   └── tests/                pytest tests, grouped by topic
└── docs/                     setup, team guide, story notes
```

## Story status

| Story | Status | Where it lives |
| --- | --- | --- |
| US-01 Public catalog | Done, 19 tests passing | `views/catalog.py`, `catalog.html`, `forms.py` |
| US-02 Accounts and roles | Not started | replaces `seed_demo_users`, extends `permissions.py` |
| US-03 Checkout | Placeholder page only | `views/checkout.py` |
| US-04 Return and damage note | Not started | new `views/` file |
| US-05 Student's own loans | Not started | new `views/` file |
| US-06 Overdue list and event log | Not started | new `views/` file |
| US-07 Admin inventory | Not started | extends `models.py`, `admin.py` |
