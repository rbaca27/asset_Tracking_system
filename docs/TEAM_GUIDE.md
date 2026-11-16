# Team guide

## How a page gets built

When someone opens `/catalog/`, Django runs these pieces in order:

1. `config/urls.py` and `inventory/urls.py` match the address to a **view**.
2. The view in `inventory/views/` asks the **model** (`models.py`) for rows. Django turns that into SQL
   and PostgreSQL returns the rows.
3. The view hands the rows to a **template** in `inventory/templates/`, which fills them into HTML.

To add a feature you usually touch one file in each layer. Put business rules (due-time math, "Repair
items cannot be checked out") in `models.py` or a small service module, not in views or templates, so
pytest can test them without clicking through pages.

## Where each story lives

| Story | View (`inventory/views/`) | Service (`inventory/services.py`) | Tests | Notes |
| --- | --- | --- | --- | --- |
| US-01 Catalog | `catalog.py` | none (read only) | `test_catalog.py` | [US-01.md](US-01.md) |
| US-02 Roster import | `roster_import.py` | `AccountService.import_roster` | `test_roster_import.py` | [US-02.md](US-02.md) |
| US-03 Checkout | `checkout.py` | `LoanService.checkout` | `test_checkout.py` | [US-03.md](US-03.md) |
| US-04 Return | `return_item.py` | `LoanService.return_item` | `test_return.py` | [US-04.md](US-04.md) |
| US-05 My loans | `my_loans.py` | none (read only) | `test_my_loans.py` | [US-05.md](US-05.md) |
| US-06 Overdue and log | `overdue.py` | `LoanService.flag_overdue` | `test_overdue.py` | [US-06.md](US-06.md) |
| US-07 Admin inventory | `admin.py` (Django admin) | `LoanService.clear_repair` | `test_admin_inventory.py` | [US-07.md](US-07.md) |
| US-08 Activation | `activate.py` | `AccountService.activate` | `test_activation.py` | [US-08.md](US-08.md) |
| US-09 Staff roles | `staff_roles.py` | `AccountService.create_staff`, `set_staff_role` | `test_staff_roles.py` | [US-09.md](US-09.md) |

Views only read data and turn service exceptions into messages. Every write that touches more than one
table goes through `services.py` inside one transaction. Role checks are `@staff_required` and
`@admin_required` in `permissions.py`.

Each story gets its own file in `views/`, its own section in `inventory/urls.py`, and its own
`tests/test_<story>.py`. That keeps teammates from editing the same files.

## The database routine

Each teammate has their own local database. What the team shares is the code that builds it.

- **You change `models.py`:** run `python manage.py makemigrations`, then `python manage.py migrate`, and
  commit the new file in `inventory/migrations/` with your change. Never edit a migration someone else
  already has.
- **You pull teammates' changes:** run `python manage.py migrate` so your tables match theirs.
- **Two people add migrations at once:** Django reports "conflicting migrations". Pull `main`, then run
  `python manage.py makemigrations --merge`.
- **Passwords:** never commit `DB_PASSWORD`. Each person sets their own in their terminal.
- **Reset your own database** (it only holds demo data): in psql run `DROP DATABASE checkout_db;` and
  `CREATE DATABASE checkout_db OWNER checkout_user;`, then repeat step 5 of `docs/SETUP.md`.

## Git routine

1. `git checkout main` and `git pull`, then `python manage.py migrate`.
2. `git checkout -b us-0X-short-name` for your story.
3. Commit small and often; run `pytest` before pushing.
4. `git push -u origin us-0X-short-name`, open a pull request on GitHub, and ask a teammate to review.

## Conventions

- One test per acceptance criterion, with the criterion in the test's docstring.
- Tests build their own data with fixtures in `tests/conftest.py`; they never rely on your local database.
- Anything a Student can see must come from a query that never touches other students' data.
