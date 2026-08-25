"""Promote CHANGELOG.md's [Unreleased] section into a released version block.

The riskiest step of preparing a release: get the promotion wrong and the
changelog silently stops being a trustworthy record. `promote_changelog`
only constructs the new text; callers must run `assert_changelog_structure`
on the result before trusting it.
"""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError

# Keep a Changelog subsection headings, in the fixed order this project's
# CHANGELOG.md uses.
SUBSECTIONS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

# `## [Unreleased]` is the one heading kept unescaped; every released version
# heading is `## \[X.Y.Z\] - YYYY-MM-DD`. Getting this backwards silently
# breaks the convention instead of failing loudly, which is exactly what
# `assert_changelog_structure` guards against.
_UNRELEASED_RE = re.compile(r"^## \[Unreleased\][ \t]*$", re.MULTILINE)
_ANY_H2_RE = re.compile(r"^## ", re.MULTILINE)
_SUBSECTION_RE = re.compile(r"^### (?P<name>\w+)[ \t]*$", re.MULTILINE)


def promote_changelog(changelog_text: str, version: str, date: str) -> str:
    """Promotes `[Unreleased]` to a released version block.

    Drops empty subsections from the promoted block, inserts a fresh empty
    `[Unreleased]` skeleton above it, and leaves everything else byte-for-byte
    unchanged. Callers must run `assert_changelog_structure` on the result
    before trusting it - this function only constructs, it doesn't verify.
    """
    unreleased_match = _single_unreleased_match(changelog_text)
    _, body_end = _unreleased_body_span(changelog_text, unreleased_match)
    sections = _parse_unreleased_sections(changelog_text)

    preamble = changelog_text[: unreleased_match.start()]
    rest = changelog_text[body_end:]

    skeleton = "## [Unreleased]\n\n" + "".join(f"### {name}\n\n" for name in SUBSECTIONS)

    promoted_sections = "".join(
        f"### {name}\n\n{sections[name].strip()}\n\n"
        for name in SUBSECTIONS
        if sections[name].strip()
    )
    promoted = f"## \\[{version}\\] - {date}\n\n" + promoted_sections

    return preamble + skeleton + promoted + rest


def assert_changelog_structure(original_text: str, new_text: str, version: str) -> None:
    r"""Verifies a changelog promotion didn't corrupt the file.

    Independently re-derives the required invariants from `new_text` rather
    than trusting how it was built, so it catches bugs in the construction
    logic itself:

    * exactly one `## [Unreleased]` heading, with all six subheadings,
    * the fresh `[Unreleased]` section has no entries,
    * exactly one new `## \\[version\\] - YYYY-MM-DD` heading, preceded by
      the `[Unreleased]` heading,
    * the promoted release block preserves the original `[Unreleased]` entries,
    * every previously-released version block is byte-identical to before.
    """
    unreleased_matches = list(_UNRELEASED_RE.finditer(new_text))
    if len(unreleased_matches) != 1:
        raise PrepareReleaseError(
            f"expected exactly one [Unreleased] heading after promotion, found "
            f"{len(unreleased_matches)}"
        )
    # Raises PrepareReleaseError itself if a subheading is missing/misordered.
    fresh_sections = _parse_unreleased_sections(new_text)
    if any(content.strip() for content in fresh_sections.values()):
        raise PrepareReleaseError(
            "expected the fresh [Unreleased] section to have no entries after promotion"
        )

    released_heading = re.compile(
        r"^## \\\[" + re.escape(version) + r"\\\] - \d{4}-\d{2}-\d{2}[ \t]*$",
        re.MULTILINE,
    )
    released_matches = list(released_heading.finditer(new_text))
    if len(released_matches) != 1:
        raise PrepareReleaseError(
            f"expected exactly one escaped '## \\[{version}\\] - YYYY-MM-DD' heading after "
            f"promotion, found {len(released_matches)}"
        )
    if released_matches[0].start() < unreleased_matches[0].start():
        raise PrepareReleaseError(
            f"expected the [Unreleased] heading to precede the new '[{version}]' release heading"
        )

    original_sections = _parse_unreleased_sections(original_text)
    expected_released_body = "".join(
        f"### {name}\n\n{original_sections[name].strip()}\n\n"
        for name in SUBSECTIONS
        if original_sections[name].strip()
    ).strip()
    if extract_released_section(changelog_text=new_text, version=version) != expected_released_body:
        raise PrepareReleaseError(
            "promoted release content does not preserve the original [Unreleased] entries"
        )

    original_match = _single_unreleased_match(original_text)
    _, original_body_end = _unreleased_body_span(original_text, original_match)
    previously_released = original_text[original_body_end:]
    if not new_text.endswith(previously_released):
        raise PrepareReleaseError(
            "previously-released changelog blocks are not byte-identical after promotion"
        )


def extract_released_section(changelog_text: str, version: str) -> str:
    r"""Returns the (trimmed) body of the `## \[version\] - ...` block.

    Consumed by the release PR body renderer (a later stage of this stack) to
    pull the just-promoted section's text into the release PR description.
    """
    heading = re.compile(
        r"^## \\\[" + re.escape(version) + r"\\\] - \d{4}-\d{2}-\d{2}[ \t]*$",
        re.MULTILINE,
    )
    match = heading.search(changelog_text)
    if match is None:
        raise PrepareReleaseError(f"no promoted heading found for version {version!r}")
    body_start = match.end()
    next_heading = _ANY_H2_RE.search(changelog_text, body_start)
    body_end = next_heading.start() if next_heading else len(changelog_text)
    return changelog_text[body_start:body_end].strip()


def _parse_unreleased_sections(changelog_text: str) -> dict[str, str]:
    """Extracts the `[Unreleased]` section's six subsections.

    Returns:
        A mapping from subsection name (e.g. "Added") to its raw body text
        (may be empty or whitespace-only).
    """
    body = _unreleased_body(changelog_text)
    headings = list(_SUBSECTION_RE.finditer(body))
    names = [h.group("name") for h in headings]
    if names != list(SUBSECTIONS):
        raise PrepareReleaseError(
            f"[Unreleased] subsections are {names}, expected {list(SUBSECTIONS)} in that order"
        )
    if body[: headings[0].start()].strip():
        raise PrepareReleaseError(
            "unexpected content between the [Unreleased] heading and its first subsection"
        )
    sections = {}
    for i, heading in enumerate(headings):
        start = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading.group("name")] = body[start:end]
    return sections


def _single_unreleased_match(changelog_text: str) -> re.Match[str]:
    matches = list(_UNRELEASED_RE.finditer(changelog_text))
    if len(matches) != 1:
        raise PrepareReleaseError(
            f"expected exactly one [Unreleased] heading, found {len(matches)}"
        )
    return matches[0]


def _unreleased_body_span(changelog_text: str, unreleased_match: re.Match[str]) -> tuple[int, int]:
    body_start = unreleased_match.end()
    next_heading = _ANY_H2_RE.search(changelog_text, body_start)
    body_end = next_heading.start() if next_heading else len(changelog_text)
    return body_start, body_end


def _unreleased_body(changelog_text: str) -> str:
    match = _single_unreleased_match(changelog_text)
    start, end = _unreleased_body_span(changelog_text, match)
    return changelog_text[start:end]
