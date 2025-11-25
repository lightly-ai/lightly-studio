"""Setup logging for the project.

Assumed to be called before any other module is imported. Make sure no internal
modules are called from this file.

Note: In python, module content is loaded only once. Therefore we can safely
put the logic in the global scope.
"""

from __future__ import annotations

import copy
import logging
import sys
import warnings
from typing import TextIO

logging.captureWarnings(capture=True)

# Set up the logger for the lightly_studio package.
lightly_logger = logging.getLogger("lightly_studio")
lightly_logger.setLevel(logging.DEBUG)


class ConsoleFormatter(logging.Formatter):
    """Custom formatter for console logging.

    This formatter uses ANSI escape codes to color log messages based on their level.
    * DEBUG     No color
    * INFO      No color
    * WARNING   Yellow
    * ERROR     Red
    * CRITICAL  Red
    The reset code is appended to each message to ensure that the color does not leak.

    The formatter does not print timestamps or log levels so as to not clutter the console.
    """

    reset = "\x1b[0m"
    log_entry_structure = "%(message)s"

    FORMATS = {
        logging.DEBUG: "\033[1;34m[debug] " + log_entry_structure + reset,
        logging.INFO: "" + log_entry_structure + reset,
        logging.WARNING: "\033[93m" + log_entry_structure + reset,
        logging.ERROR: "\033[91m" + log_entry_structure + reset,
        logging.CRITICAL: "\033[91m" + log_entry_structure + reset,
    }

    def __init__(self) -> None:
        self.formatters = {
            level: logging.Formatter(level_format)
            for level, level_format in ConsoleFormatter.FORMATS.items()
        }
        self.default_formatter = logging.Formatter(fmt=self.log_entry_structure)

    def format(self, record: logging.LogRecord) -> str:
        new_record = copy.copy(record)
        formatter = self.formatters.get(new_record.levelno, self.default_formatter)
        return formatter.format(new_record)


def set_up_console_logging(level: int | str = logging.INFO) -> None:
    """Sets up console logging and ensures a single handler per console logger."""
    level_value = _coerce_level(level)
    lightly_logger.setLevel(logging.DEBUG)
    logging.getLogger().setLevel(level_value)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level_value)
    handler.setFormatter(ConsoleFormatter())
    _set_console_handler(handler)


def _coerce_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper(), logging.INFO)


def _set_console_handler(handler: "logging.StreamHandler[TextIO]") -> None:
    """Sets this handler as the only handler printing to the console.

    Removes all existing stream handlers.
    """
    console_loggers = [
        logging.getLogger(),
        lightly_logger,
        logging.getLogger("py.warnings"),
    ]

    for console_logger in console_loggers:
        _remove_handlers(console_logger, logging.StreamHandler)
        console_logger.addHandler(handler)


def _remove_handlers(
    logger: logging.Logger,
    handler_cls_to_remove: type[logging.Handler] = logging.Handler,
) -> None:
    """Removes all handlers of the given class from the logger."""
    new_handlers = []
    for handler in logger.handlers:
        # NullHandler should never be removed as it prevents messages from being
        # printed to stderr. See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
        if isinstance(handler, logging.NullHandler) or not isinstance(
            handler, handler_cls_to_remove
        ):
            new_handlers.append(handler)
    logger.handlers = new_handlers


# Set logging level to ERROR for labelformat.
logging.getLogger("labelformat").setLevel(logging.ERROR)

# Suppress warnings from mobileclip.
# TODO(Michal, 04/2025): Remove once we don't vendor mobileclip.
warnings.filterwarnings("ignore", category=FutureWarning, module="timm.models.layers")
warnings.filterwarnings("ignore", category=FutureWarning, module="mobileclip")

# Configure console logging immediately when the module is imported.
set_up_console_logging()
