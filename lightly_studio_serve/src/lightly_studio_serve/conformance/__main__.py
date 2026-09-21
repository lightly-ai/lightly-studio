"""Runs the conformance kit from a terminal.

``python -m lightly_studio_serve.conformance <url>`` ends with 0 for a server that passes,
so a customer can run it in their own build.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from lightly_studio_serve.conformance import report as report_module
from lightly_studio_serve.conformance import runner
from lightly_studio_serve.conformance.client import HttpProbeClient

API_KEY_VARIABLE = "LIGHTLY_STUDIO_SERVE_API_KEY"
"""The variable that holds the key, so no terminal history keeps it."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the kit against one server and write the report.

    Args:
        argv: The arguments to read. ``None`` reads the ones of the process.

    Returns:
        The exit status: 0 for a server that passes, 1 for one that does not.
    """
    arguments = _parse(argv=argv)
    try:
        client = HttpProbeClient(base_url=arguments.url, api_key=arguments.api_key)
    # A person reads this, not a traceback.
    except ValueError as error:
        print(error)
        return 1
    report = runner.check_conformance(client=client, probe_timeout=arguments.probe_timeout)
    print(f"{arguments.url}\n")
    print(report_module.render(report=report))
    print(f"\n{'PASSED' if report.passed else 'FAILED'}")
    return 0 if report.passed else 1


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m lightly_studio_serve.conformance",
        description=(
            "Check that a server implements the LightlyStudio embedding protocol. The run "
            "reads /v1/describe, then sends one fixed probe per advertised capability."
        ),
    )
    parser.add_argument("url", help="The address of the server, e.g. http://127.0.0.1:8080.")
    parser.add_argument(
        "--api-key",
        default=os.environ.get(API_KEY_VARIABLE),
        help=f"The bearer token the server expects. Defaults to ${API_KEY_VARIABLE}.",
    )
    parser.add_argument(
        "--probe-timeout",
        type=_positive_seconds,
        default=runner.PROBE_TIMEOUT_SECONDS,
        help="The seconds one probe may take. Default: %(default)s.",
    )
    return parser.parse_args(argv)


def _positive_seconds(value: str) -> float:
    """Read a timeout, rejecting the ones under which every probe fails by definition."""
    seconds = float(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError(f"must be over 0 seconds, got {value}.")
    return seconds


if __name__ == "__main__":
    sys.exit(main())
