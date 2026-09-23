from __future__ import annotations

from pathlib import Path

import pytest

from prepare_release import changelog, slack_message
from prepare_release.errors import PrepareReleaseError

URL = "https://x/y"

# The repository root, from `.github/scripts/tests/`.
REPOSITORY = Path(__file__).parents[3]

SECTION = """\
### Added

- Added thing one.
- Added thing two.

### Deprecated

### Fixed

- Fixed thing three.\
"""

GROUPED = """\
### Added

- Distribution plot
    - Compare by sample tag.
    - Compare by metadata.

- Sampling
    - Continue from an existing selection.\
"""

WRAPPED = """\
### Removed

- Remove the classifier export format. Downloading a classifier no longer asks for a
  format and always writes the scikit-learn format.\
"""


def render(section_body: str, **kwargs: object) -> str:
    kwargs.setdefault("display_name", "LightlyStudio")
    return slack_message.render_slack_message(
        section_body=section_body, version="1.1.0", release_url=URL, **kwargs
    )


def test_render_slack_payload():
    payload = slack_message.render_slack_payload(
        section_body=SECTION,
        version="1.1.0",
        release_url=URL,
        display_name="LightlyStudio",
        channel="studio-issues-and-feedback",
    )

    assert payload["channel"] == "studio-issues-and-feedback"
    assert payload["text"] == render(SECTION)


# The title links to the release page, so without this every announcement grows a preview
# card of it.
def test_render_slack_payload__unfurling_off():
    payload = slack_message.render_slack_payload(
        section_body=SECTION,
        version="1.1.0",
        release_url=URL,
        display_name="LightlyStudio",
        channel="studio-issues-and-feedback",
    )

    assert payload["unfurl_links"] is False
    assert payload["unfurl_media"] is False


def test_render_slack_payload__no_entries():
    with pytest.raises(PrepareReleaseError, match="has no entries"):
        slack_message.render_slack_payload(
            section_body="### Added\n",
            version="1.1.0",
            release_url=URL,
            display_name="LightlyStudio",
            channel="studio-issues-and-feedback",
        )


# Pins the whole shape: the linked title, a bare heading with no blank line under it, no
# blank line between sections, and the empty `Deprecated` heading dropped.
def test_render_slack_message():
    assert render(SECTION) == (
        f"*<{URL}|LightlyStudio Release 1.1.0>*\n"
        "\n"
        "Added\n"
        "• Added thing one.\n"
        "• Added thing two.\n"
        "Fixed\n"
        "• Fixed thing three."
    )


# Blank lines survive between bullets, where they separate the named groups of a large
# release, and nowhere else.
def test_render_slack_message__nested_bullets():
    assert render(GROUPED) == (
        f"*<{URL}|LightlyStudio Release 1.1.0>*\n"
        "\n"
        "Added\n"
        "• Distribution plot\n"
        "    ◦ Compare by sample tag.\n"
        "    ◦ Compare by metadata.\n"
        "\n"
        "• Sampling\n"
        "    ◦ Continue from an existing selection."
    )


def test_render_slack_message__title_names_the_package():
    message = render(SECTION, display_name="LightlyStudio Serve")

    assert message.startswith(f"*<{URL}|LightlyStudio Serve Release 1.1.0>*\n\n")


@pytest.mark.parametrize(
    ("indent", "expected_marker"),
    [
        ("", "• "),
        # A single space is a typo, not a nesting level. One 0.4.13 entry has one.
        (" ", "• "),
        ("    ", "    ◦ "),
    ],
)
def test_render_slack_message__bullet_markers(indent: str, expected_marker: str):
    section = f"### Added\n\n- A parent.\n{indent}- A child.\n"

    assert f"{expected_marker}A child." in render(section)


def test_render_slack_message__joins_continuation_lines():
    assert "• Remove the classifier export format. " in render(WRAPPED)
    assert "asks for a format and always writes" in render(WRAPPED)


# Slack renders a code span the way the changelog means it, so backticks pass through,
# and it only applies `_italic_` at word boundaries, so `max_concurrency` is safe.
def test_render_slack_message__keeps_code_spans_and_underscores():
    section = "### Added\n\n- Accept `target_fps`, and raise `max_concurrency`.\n"

    assert "`target_fps`, and raise `max_concurrency`." in render(section)


# Slack reads these three as control characters - `tag_depth > 1` occurs twice in 1.1.0.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("tag_depth > 1", "tag_depth &gt; 1"),
        ("a < b", "a &lt; b"),
        ("a & b", "a &amp; b"),
        ("nothing to escape", "nothing to escape"),
    ],
)
def test_escape_slack_text(text: str, expected: str):
    assert slack_message.escape_slack_text(text) == expected


def test_render_slack_message__no_entries():
    with pytest.raises(PrepareReleaseError, match="has no entries"):
        render("### Added\n\n### Fixed\n")


# Cut back to a whole bullet, and never leave a heading with nothing under it. The limit
# is one character under what GROUPED renders to, so exactly one round of cutting runs.
def test_render_slack_message__truncates_to_whole_entries():
    message = render(GROUPED, character_limit=180)

    assert message == (
        f"*<{URL}|LightlyStudio Release 1.1.0>*\n"
        "\n"
        "Added\n"
        "• Distribution plot\n"
        "    ◦ Compare by sample tag.\n"
        "\n"
        f"…\nFull changelog: <{URL}|LightlyStudio Release 1.1.0 on GitHub>"
    )


def test_render_slack_message__limit_too_small():
    with pytest.raises(PrepareReleaseError, match="exceeds 10 characters"):
        render(GROUPED, character_limit=10)


# The rules exist because of what the real changelogs contain, so they are checked against
# the real changelogs and not only against the fixtures above. 1.1.0 is the awkward one:
# an empty `Deprecated` heading, grouped bullets, wrapped entries and a literal `>`.
@pytest.mark.parametrize(
    ("changelog_path", "version"),
    [("CHANGELOG.md", "1.1.0"), ("lightly_studio_serve/CHANGELOG.md", "0.1.0")],
)
def test_render_slack_message__real_changelog_section(changelog_path: str, version: str):
    section = changelog.extract_released_section(
        changelog_text=(REPOSITORY / changelog_path).read_text(), version=version
    )

    message = slack_message.render_slack_message(
        section_body=section, version=version, release_url=URL, display_name="LightlyStudio"
    )

    assert len(message) <= slack_message.CHARACTER_LIMIT
    assert "Full changelog" not in message
    assert "\n\n\n" not in message
    assert not any(line.startswith(("### ", "- ", "    - ")) for line in message.splitlines())


def test_render_slack_message__real_changelog_section__1_1_0():
    section = changelog.extract_released_section(
        changelog_text=(REPOSITORY / "CHANGELOG.md").read_text(), version="1.1.0"
    )

    message = slack_message.render_slack_message(
        section_body=section, version="1.1.0", release_url=URL, display_name="LightlyStudio"
    )

    assert "Deprecated" not in message
    assert "• Distribution plot\n    ◦ Compare the annotation class" in message
    assert "`tag_depth &gt; 1`" in message
