"""LightlyStudio plugins module."""

from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.services.plugin_server_manager import plugin_server_manager

# Auto-discover operators from externally installed packages
# (registered via entry points in their pyproject.toml)
operator_registry.discover_plugins()

# Start servers for operators that declare one
plugin_server_manager.start_all(operator_registry)
