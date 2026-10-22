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

## Where each story goes

| Story | Add or change |
| --- | --- |
| US-02 Accounts and roles | Create the Student, Staff and Admin groups and real seeded users; delete `seed_demo_users.py`; add Panther ID, email and phone (a `Profile` model); add them to the `student` fixture in `tests/conftest.py` and the secret list in `test_catalog_hides_borrower_fields` |
| US-03 Checkout | Add a `Loan` model, fill in `views/checkout.py` (keep `@staff_required`), add a template; switch `test_catalog_reflects_status_change` to use it |
| US-04 Return and damage note | New `views/return_item.py`, URL, template; a return sets status to Available or Repair |
| US-05 Student's own loans | New `views/my_loans.py`; filter loans by `request.user`, never by an ID in the URL |
| US-06 Overdue list and log | New `views/overdue.py` and an event-log model; Staff only |
| US-07 Admin inventory | Extend `models.py` and `admin.py`; `loan_duration` and `is_retired` already exist |

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
