"""LightlyStudio plugins module."""

from lightly_studio.plugins.operator_registry import operator_registry

# Auto-discover operators from externally installed packages
# (registered via entry points in their pyproject.toml).
# Startup (start()) is handled by the FastAPI lifespan in app.py.
operator_registry.discover_plugins()
