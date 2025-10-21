"""Setup logging for the project.

Assumed to be called before any other module is imported. Make sure no internal
modules are called from this file.

Note: In python, module content is loaded only once. Therefore we can safely
put the logic in the global scope.
"""

import logging
import warnings

# Set logging level to ERROR for labelformat.
logging.getLogger("labelformat").setLevel(logging.ERROR)

# Suppress warnings from mobileclip.
# TODO(Michal, 04/2025): Remove once we don't vendor mobileclip.
warnings.filterwarnings("ignore", category=FutureWarning, module="timm.models.layers")
warnings.filterwarnings("ignore", category=FutureWarning, module="mobileclip")
