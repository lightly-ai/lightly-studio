"""Allows invocation as `python -m prepare_release <subcommand> ...`."""

import sys

from prepare_release.cli import main

if __name__ == "__main__":
    sys.exit(main())
