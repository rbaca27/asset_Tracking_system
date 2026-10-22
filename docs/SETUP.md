# Setup on a Mac with PyCharm (free edition works)

Everything happens in PyCharm's **Terminal** tab (bottom of the window, or View > Tool Windows >
Terminal). It opens in the project folder, so you only paste commands. You do this once per computer.

**1. Open the folder.** PyCharm > File > Open > the `equipment-checkout` folder.

**2. Make the virtual environment and install the packages.** A virtual environment (`.venv`) is a private
folder of Python packages for this project.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Your prompt now starts with `(.venv)`. Without it, plain `python` does not exist on a Mac. Then tell PyCharm
to use it: Settings > Project > Python Interpreter > Add Interpreter > Add Local Interpreter > Existing,
and pick `.venv/bin/python`.

**3. Create the database.** PostgreSQL must be running (Postgres.app: click Start).

```bash
psql postgres
```

Paste these three lines, then type `\q` to leave. The password is yours to pick; the project only needs this one.

```sql
CREATE USER checkout_user WITH PASSWORD 'pick-a-password';
CREATE DATABASE checkout_db OWNER checkout_user;
ALTER USER checkout_user CREATEDB;
```

If `psql` says "command not found" with Postgres.app, run
`echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc`,
then close and reopen the Terminal tab.

**4. Give Django the password** (the one from step 3):

```bash
export DB_PASSWORD=pick-a-password
```

This lasts only for that Terminal tab. In a new tab or after restarting PyCharm, run it again, and run
`source .venv/bin/activate` if the prompt has no `(.venv)`.

**5. Build the tables and load demo data.**

```bash
python manage.py migrate
python manage.py loaddata assets
python manage.py seed_demo_users
```

`migrate` creates the tables. `loaddata assets` adds 15 demo items. `seed_demo_users` creates logins
`student1`, `staff1` and `admin1`, all with password `demo-pass-123`.

**6. Run the site.**

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/catalog/. Press Ctrl+C in the Terminal to stop it.

**7. Run the tests** (in a Terminal tab where step 4 was done).

```bash
pytest -v
```

All tests should pass.

## When something goes wrong

| You see | Fix |
| --- | --- |
| `zsh: command not found: python` | Run `source .venv/bin/activate`, or type `python3` |
| `password authentication failed` or `connection refused` | Postgres is not running, or `DB_PASSWORD` is not set in this Terminal tab (step 4) |
| `permission denied to create database` when running pytest | Run `ALTER USER checkout_user CREATEDB;` in psql |
| `No module named django` | The `.venv` is not active; see step 2 |
