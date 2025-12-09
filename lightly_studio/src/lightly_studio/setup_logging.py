"""Setup logging for the project.

Assumed to be called before any other module is imported. Make sure no internal
modules are called from this file.

Note: In python, module content is loaded only once. Therefore we can safely
put the logic in the global scope.
"""

import logging
import warnings
from typing import ClassVar


class ConsoleFormatter(logging.Formatter):
    """Customer console formatter for Lightly Studio."""

    green = "\x1b[33;32m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    time_str = "%(asctime)s "
    level_str = "%(levelname)s" + reset + ": "
    msg_str = "%(message)s"

    FORMATS: ClassVar = {
        logging.DEBUG: time_str + level_str + msg_str,
        logging.INFO: time_str + green + level_str + msg_str,
        logging.WARNING: time_str + yellow + level_str + msg_str,
        logging.ERROR: time_str + red + level_str + msg_str,
        logging.CRITICAL: time_str + bold_red + level_str + msg_str,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format record using our own format and colors."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Set logging level to ERROR for labelformat.
logging.getLogger("labelformat").setLevel(logging.ERROR)

# Configure the root logger with ConsoleFormatter
root_logger = logging.getLogger()
# Do not add a new logging handler if there's one registered already. This prevents duplicated
# log messages.
if not root_logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)  # TODO(lukas 12/2025): Make this configurable
    ch.setFormatter(ConsoleFormatter())
    root_logger.addHandler(ch)
root_logger.setLevel(logging.INFO)  # TODO(lukas 12/2025): Make this configurable

# Suppress warnings from mobileclip.
# TODO(Michal, 04/2025): Remove once we don't vendor mobileclip.
warnings.filterwarnings("ignore", category=FutureWarning, module="timm.models.layers")
warnings.filterwarnings("ignore", category=FutureWarning, module="mobileclip")
