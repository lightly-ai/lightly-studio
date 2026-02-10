"""Auto-labeling module for Lightly Studio."""

from lightly_studio.auto_labeling.provider_registry import provider_registry
from lightly_studio.auto_labeling.providers.chatgpt_captioning import (
    ChatGPTCaptioningProvider,
)
from lightly_studio.auto_labeling.providers.open_vocabulary_detector import (
    OpenVocabularyDetectorProvider,
)

# Register all providers at module import
provider_registry.register(ChatGPTCaptioningProvider())
provider_registry.register(OpenVocabularyDetectorProvider())
