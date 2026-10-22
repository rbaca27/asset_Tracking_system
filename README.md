# Equipment Checkout: US-01 Public Catalog

Students browse the equipment catalog by type, location and status. Checked Out and
Repair items show as unavailable, and no borrower details ever appear.

## Run it in PyCharm (Mac)

1. **Open the folder.** PyCharm > File > Open > `Desktop/Adv. Software eng/equipment-checkout`.
2. **Make the interpreter.** When PyCharm asks to configure a Python interpreter, choose
   *Add New Interpreter > Virtualenv*, location `.venv` inside the project. When it offers to install
   from `requirements.txt`, click **Install**. (Or open the Terminal tab and run
   `pip install -r requirements.txt`.)
3. **Create the database.** PostgreSQL must be running (Postgres.app: click Start). In the Terminal tab:

   ```bash
   psql postgres
   ```

   then paste these three lines and type `\q` to leave:

   ```sql
   CREATE USER checkout_user WITH PASSWORD 'pick-a-password';
   CREATE DATABASE checkout_db OWNER checkout_user;
   ALTER USER checkout_user CREATEDB;
   ```

   If `psql` is "command not found" with Postgres.app, run
   `sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp`
   and reopen PyCharm.
4. **Give Django the password.** Run > Edit Configurations > the Django server (or add a
   *Django Server* configuration) > Environment variables: `DB_PASSWORD=pick-a-password`.
   Do the same in the pytest template (Edit Configurations > Edit configuration templates > Python tests > pytest).
5. **Build the tables and load demo data.** Tools > Run manage.py Task, then run each:
   - `migrate`
   - `loaddata assets` (15 demo items)
   - `seed_demo_users` (logins `student1`, `staff1`, `admin1`, password `demo-pass-123`)
   - `createsuperuser` (optional, for the admin site)

   If the manage.py console can't see the password, set `DB_PASSWORD` under
   Settings > Languages & Frameworks > Django > Environment variables.
6. **Run the site.** Click the green Run button and open http://127.0.0.1:8000/catalog/.
7. **Run the tests.** Settings > Tools > Python Integrated Tools > Default test runner: **pytest**.
   Then right-click the `inventory/tests` folder > Run 'pytest in tests'. All 19 should pass.

## What's where

| File | What it does |
| --- | --- |
| `inventory/models.py` | `Asset` table: tag, type, location, status, loan duration, retired flag |
| `inventory/migrations/0001_initial.py` | Creates that table in PostgreSQL |
| `inventory/fixtures/assets.json` | 15 demo items, including Checked Out, Repair and one retired |
| `inventory/forms.py` | Catalog filter boxes |
| `inventory/views.py` | Catalog page, plus a Staff-only placeholder checkout page for US-03 |
| `inventory/permissions.py` | `staff_required`: signed out goes to sign-in, Students get 403 |
| `inventory/templates/` | `base.html` layout, the catalog page and the sign-in page |
| `inventory/management/commands/seed_demo_users.py` | Temporary demo logins until US-02 lands |
| `inventory/tests/` | 19 pytest tests covering every US-01 acceptance criterion |

## Acceptance criteria and tests

| Acceptance criterion | Test |
| --- | --- |
| Rows show tag, type, location, status | `test_catalog_row_shows_four_fields` |
| Status is one of three values | `test_status_limited_to_three_choices`, `test_database_refuses_unknown_status` |
| Checked Out and Repair badged unavailable | `test_unavailable_items_visible_and_badged` |
| No borrower name, Panther ID, email or phone | `test_catalog_hides_borrower_fields` |
| Student cannot open checkout form | `test_student_gets_403_on_checkout` |
| Catalog shows new status after checkout or return | `test_catalog_reflects_status_change` |

## Notes for teammates

- **US-02:** replace `seed_demo_users` with the real accounts, and add mock Panther ID and phone to the
  `student` fixture in `inventory/tests/conftest.py` and to the privacy test's list.
- **US-03 / US-04:** keep `@staff_required` on `checkout` and replace its body. Switch
  `test_catalog_reflects_status_change` to call your checkout and return code.
- **US-07:** the `Asset` model already has `loan_duration` and `is_retired`; extend it with a new migration.
- **Sergio:** `base.html` is a minimal layout; restyle freely.
