"""Shared Alembic config helpers for migration entrypoints."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from lightly_studio.database import db_url


def ensure_script_location(config: Config, migrations_dir: Path) -> None:
    """Point Alembic at the migrations package when ini path is not valid."""
    script_location = config.get_main_option(name="script_location")
    if script_location is not None and Path(script_location).is_dir():
        return
    config.set_main_option(name="script_location", value=str(migrations_dir))


def find_alembic_ini(package_dir: Path) -> Path:
    """Return the path to alembic.ini for development or installed layouts."""
    installed_ini = package_dir / "alembic.ini"
    if installed_ini.is_file():
        return installed_ini

    dev_ini = package_dir.parent.parent / "alembic.ini"
    if dev_ini.is_file():
        return dev_ini

    raise FileNotFoundError("alembic.ini not found for Alembic migrations.")


def database_url_configured(config: Config) -> bool:
    """Return whether migrations can run without reading env database URL."""
    if config.attributes.get("connection") is not None:
        return True
    url = config.get_main_option(name="sqlalchemy.url")
    return url is not None and url.strip() != ""


def configure_database_url(config: Config, engine_url: str | None) -> None:
    """Set sqlalchemy.url from engine_url when not already configured."""
    if database_url_configured(config=config):
        return
    if engine_url is None:
        raise RuntimeError("LIGHTLY_STUDIO_DATABASE_URL must be set for Alembic CLI migrations.")
    config.set_main_option(
        name="sqlalchemy.url",
        value=db_url.ensure_psycopg3_driver(engine_url=engine_url),
    )
