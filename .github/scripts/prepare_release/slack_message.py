"""Render a released changelog section as the Slack message that announces it.

Backs the "Announce Release" workflow. Sales reads `#studio-issues-and-feedback` rather
than the GitHub releases page, so the changelog section is posted there - a copy-paste
somebody did by hand until now, which is why the format drifted between releases and why
code spans kept getting lost on the way.

Slack's mrkdwn is not Markdown: it has no list syntax, no headings, and `&`, `<` and `>`
are control characters. `_render_entries` is every rule that follows from that, and the
tests check it against the repository's real changelogs - which is the only way to find
out what those actually contain.
"""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError

# Slack accepts 40000 characters in `text`. This is the ceiling that keeps a freak release
# from failing the post, not a readability limit: Slack folds anything past roughly 4000
# behind "Show more", which costs a click, where truncating would cost the entries. A
# minor release renders to about 5000, so nothing is dropped in practice.
CHARACTER_LIMIT = 39_000

# Slack has no list syntax, so a bullet is a literal character and nesting is an indent.
# Truncation keeps whole entries by cutting back to one of these.
_MARKERS = ("• ", "    ◦ ")

# Bullets indented less than a full step are top level. Not "indented at all": one 0.4.13
# entry carries a single leading space and is not a child of anything.
_NESTED_INDENT = 4

_HEADING_RE = re.compile(r"^### (?P<name>\w+)[ \t]*$")
_BULLET_RE = re.compile(r"^(?P<indent> *)- (?P<text>.+)$")

_TITLE = "*<{url}|{display_name} Release {version}>*"
_TRUNCATION_TAIL = "…\nFull changelog: <{url}|{display_name} Release {version} on GitHub>"


def render_slack_payload(
    section_body: str,
    version: str,
    release_url: str,
    display_name: str,
    channel: str,
) -> dict[str, str | bool]:
    """Renders a released changelog section as a `chat.postMessage` request body.

    The whole request, not just its `text`, so the announcement's shape is covered by
    these tests rather than by the workflow that posts it.

    Args:
        section_body: The `[X.Y.Z]` block, as returned by `changelog.extract_released_section`.
        version: The version being announced, e.g. "1.1.0".
        release_url: The GitHub release page. Linked from the title, so a truncated message
            always has somewhere to send the reader.
        display_name: The product name the title announces, to tell two packages apart in
            one channel.
        channel: The channel to post in, e.g. "studio-issues-and-feedback".

    Returns:
        The request body for `chat.postMessage`.

    Raises:
        PrepareReleaseError: The section has no entries, or not even its first entry fits
            `character_limit`.
    """
    return {
        "channel": channel,
        "text": render_slack_message(
            section_body=section_body,
            version=version,
            release_url=release_url,
            display_name=display_name,
        ),
        # The title links to the GitHub release. Unfurled, every announcement grows a
        # preview card of that page under the entries.
        "unfurl_links": False,
        "unfurl_media": False,
    }


def render_slack_message(
    section_body: str,
    version: str,
    release_url: str,
    display_name: str,
    character_limit: int = CHARACTER_LIMIT,
) -> str:
    """Renders a released changelog section as Slack mrkdwn.

    Args:
        section_body: The `[X.Y.Z]` block, as returned by `changelog.extract_released_section`.
        version: The version being announced, e.g. "1.1.0".
        release_url: The GitHub release page. Linked from the title, so a truncated message
            always has somewhere to send the reader.
        display_name: The product name the title announces, to tell two packages apart in
            one channel.
        character_limit: Longest message to produce, the truncation tail included.

    Returns:
        The `text` for `chat.postMessage`, without a trailing newline.

    Raises:
        PrepareReleaseError: The section has no entries, or not even its first entry fits
            `character_limit`.
    """
    entries = _render_entries(section_body=section_body)
    if not entries:
        raise PrepareReleaseError(f"changelog section for {version} has no entries")

    title = _TITLE.format(url=release_url, display_name=display_name, version=version)
    message = "\n".join([title, "", *entries])
    if len(message) <= character_limit:
        return message

    tail = _TRUNCATION_TAIL.format(url=release_url, display_name=display_name, version=version)
    return _truncate(
        entries=entries, title=title, tail=tail, character_limit=character_limit, version=version
    )


def escape_slack_text(text: str) -> str:
    """Escapes the three characters Slack's mrkdwn parser reads as control characters.

    `&`, `<` and `>` only. Backticks pass through because Slack renders a code span the
    same way the changelog means it, and `*` and `_` pass through because Slack only
    applies them at word boundaries - which is what makes `max_concurrency` safe. An entry
    written with genuine `_emphasis_` does render as italics; mrkdwn has no escape for
    that other than backticks.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_entries(section_body: str) -> list[str]:
    """Renders the bullets, each preceded by its heading the first time one follows it.

    Holding the heading back until a bullet arrives is what drops the empty sections - a
    released block regularly carries a heading with nothing under it. A blank line is kept
    only between bullets, where it separates the named groups of a large release, and
    never before a heading, where the source always has one and the post never does.
    """
    lines: list[str] = []
    heading = ""
    blank_pending = False
    for line in _join_continuations(section_body.splitlines()):
        if not line.strip():
            blank_pending = True
            continue
        section = _HEADING_RE.match(line)
        if section is not None:
            heading, blank_pending = section["name"], False
            continue
        bullet = _BULLET_RE.match(line)
        if bullet is None:
            continue
        if heading:
            lines.append(heading)
            heading, blank_pending = "", False
        if blank_pending:
            lines.append("")
        marker = _MARKERS[0] if len(bullet["indent"]) < _NESTED_INDENT else _MARKERS[1]
        lines.append(marker + escape_slack_text(bullet["text"].strip()))
        blank_pending = False
    return lines


def _join_continuations(lines: list[str]) -> list[str]:
    """Joins a wrapped entry back onto the bullet it continues.

    Changelog entries wrap at the column limit and continue on an indented line. A line
    that continues nothing - which `extract_released_section` should never hand over - is
    left where it is, and `_render_entries` then ignores it.
    """
    joined: list[str] = []
    for line in lines:
        continues_an_entry = line.strip() and joined and joined[-1].strip()
        if continues_an_entry and _BULLET_RE.match(line) is None:
            joined[-1] = f"{joined[-1]} {line.strip()}"
        else:
            joined.append(line)
    return joined


def _truncate(entries: list[str], title: str, tail: str, character_limit: int, version: str) -> str:
    """Drops rendered lines from the end until the message and its tail fit.

    Cutting back to a bullet each time keeps an entry whole and leaves no heading behind
    with nothing under it. Children follow their parent, so they go first.
    """
    kept = list(entries)
    while kept:
        while kept and not kept[-1].startswith(_MARKERS):
            kept.pop()
        if not kept:
            break
        message = "\n".join([title, "", *kept, "", tail])
        if len(message) <= character_limit:
            return message
        kept.pop()
    raise PrepareReleaseError(
        f"the announcement for {version} exceeds {character_limit} characters "
        f"even with a single entry"
    )
