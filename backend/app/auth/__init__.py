"""User accounts: registration, login sessions, profiles and preferences.

Accounts live in their OWN database (AUTH_DATABASE_URL, default `patent_rag_auth`),
separate from the patent data, with their own tables and migrations (alembic_auth/).
Other tables refer to users only by id (`owner_id`); there are no cross-database
foreign keys.

    passwords.py   scrypt password hashing (Python standard library)
    db.py          the auth database engine and session
    models.py      users, login sessions
    service.py     register, login, logout, profile, password change
    deps.py        FastAPI dependencies: the current user from the session cookie
    routes.py      /auth/* endpoints
"""
