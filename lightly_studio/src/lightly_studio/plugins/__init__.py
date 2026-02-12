"""LightlyStudio plugins module."""

from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.operators.chatgpt_captioning import (
    ChatGPTCaptioningOperator,
)
from lightly_studio.plugins.operators.open_vocabulary_detector import (
    OpenVocabularyDetectorOperator,
)
from lightly_studio.services.plugin_server_manager import plugin_server_manager

# Register built-in batch sample operators with deterministic IDs
operator_registry.register(
    ChatGPTCaptioningOperator(), operator_id="chatgpt_captioning"
)
operator_registry.register(
    OpenVocabularyDetectorOperator(), operator_id="open_vocabulary_detector"
)

# Auto-discover operators from externally installed packages
operator_registry.discover_plugins()

# Start servers for operators that declare one
plugin_server_manager.start_all(operator_registry)
