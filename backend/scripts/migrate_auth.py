"""Create (if missing) and migrate the separate auth database.

cd backend && .venv/bin/python -m scripts.migrate_auth [--test]
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.auth.config import get_auth_settings

BACKEND = Path(__file__).resolve().parents[1]


def ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
            print(f"Created database {target.database}")
    admin.dispose()


def migrate(url: str) -> None:
    ensure_database(url)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic_auth"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def main() -> int:
    settings = get_auth_settings()
    url = settings.auth_test_database_url if "--test" in sys.argv else settings.auth_database_url
    migrate(url)
    print(f"Auth database {make_url(url).database} is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
