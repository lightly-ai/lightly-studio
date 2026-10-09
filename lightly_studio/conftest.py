"""Root conftest loaded before any test-directory conftest.

Sets the analytics flag before lightly_studio is first imported.  tracking.py
calls _get_tracker() at module level when LIGHTLY_STUDIO_ANALYTICS_ENABLED is
true; disabling it here prevents PostHogTracker construction and the
install_id file from appearing during test runs.
"""

import os

os.environ["LIGHTLY_STUDIO_ANALYTICS_ENABLED"] = "0"
