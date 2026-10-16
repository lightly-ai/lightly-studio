"""Helpers for the assisted labeling service tests."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import settings_resolver


def select_provider(session: Session, provider_id: str) -> None:
    """Selects the assisted labeling provider in the settings."""
    settings = settings_resolver.get_settings(session=session)
    settings_resolver.set_settings(
        session=session,
        settings=settings.model_copy(update={"assisted_labeling_provider": provider_id}),
    )
