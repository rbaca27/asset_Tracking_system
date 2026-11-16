"""Views, one module per story so teammates on different stories rarely edit the same file.

catalog.py        US-01  public catalog and search
roster_import.py  US-02  Admin roster CSV import
checkout.py       US-03  Staff walk-up checkout
return_item.py    US-04  Staff return with optional damage note
my_loans.py       US-05  a student's own loans and profile
overdue.py        US-06  Staff overdue list and in-app event log
                  US-07  Admin inventory lives in the Django admin site (inventory/admin.py)
activate.py       US-08  one-time account activation (sign-in itself is Django's LoginView)
staff_roles.py    US-09  Admin creates Staff accounts and assigns the Staff role

Views only read data and translate service exceptions into messages. Every write goes through
inventory/services.py. Register each URL in inventory/urls.py.
"""
