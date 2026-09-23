import pytest

from prepare_release import changelog
from prepare_release.errors import PrepareReleaseError

SAMPLE_CHANGELOG = """\
# Changelog

All notable changes to Lightly**Studio** will be documented in this file.

## [Unreleased]

### Added

- Added thing one.

### Changed

- Changed thing one.

### Deprecated

### Removed

### Fixed

### Security

## \\[1.0.5\\] - 2026-08-14

### Added

- Some old thing.

## \\[1.0.4\\] - 2026-08-01

### Fixed

- An older fix.
"""


def test_promote_changelog() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )

    # Fresh, fully-empty [Unreleased] skeleton with all six subheadings.
    assert promoted.count("## [Unreleased]") == 1
    fresh_sections = changelog._parse_unreleased_sections(promoted)
    assert list(fresh_sections) == list(changelog.SUBSECTIONS)
    assert all(not content.strip() for content in fresh_sections.values())

    # New release heading in escaped form, empty sections dropped.
    assert "## \\[1.1.0\\] - 2026-08-21" in promoted
    assert "Added thing one" in promoted
    assert "Changed thing one" in promoted

    # Previously-released blocks are untouched.
    assert "## \\[1.0.5\\] - 2026-08-14" in promoted
    assert "## \\[1.0.4\\] - 2026-08-01" in promoted
    assert promoted.index("1.1.0") < promoted.index("1.0.5") < promoted.index("1.0.4")

    changelog.assert_changelog_structure(
        original_text=SAMPLE_CHANGELOG, new_text=promoted, version="1.1.0"
    )


def test_assert_changelog_structure__missing_unreleased_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    corrupted = promoted.replace("## [Unreleased]\n\n", "", 1)
    with pytest.raises(PrepareReleaseError):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_assert_changelog_structure__entry_left_in_fresh_unreleased_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    corrupted = promoted.replace(
        "## [Unreleased]\n\n### Added",
        "## [Unreleased]\n\n### Added\n\n- Leftover entry.",
        1,
    )
    with pytest.raises(PrepareReleaseError, match="no entries"):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_assert_changelog_structure__dropped_entry_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    corrupted = promoted.replace("- Added thing one.\n\n", "", 1)
    with pytest.raises(PrepareReleaseError, match="does not preserve"):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_assert_changelog_structure__mutated_released_block_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    corrupted = promoted.replace("An older fix.", "A DIFFERENT fix.")
    with pytest.raises(PrepareReleaseError, match="byte-identical"):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_assert_changelog_structure__missing_new_heading_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    corrupted = promoted.replace("## \\[1.1.0\\] - 2026-08-21", "## [1.1.0] - 2026-08-21")
    with pytest.raises(PrepareReleaseError):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_assert_changelog_structure__duplicate_new_heading_raises() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.0.5", date="2026-08-24"
    )
    with pytest.raises(PrepareReleaseError, match="exactly one"):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=promoted, version="1.0.5"
        )


def test_assert_changelog_structure__unreleased_after_release_heading_raises() -> None:
    # Every other check would pass here (single [Unreleased] heading with
    # valid subsections, the new release heading present exactly once, the
    # previously-released suffix byte-identical) - only the ordering is
    # wrong: the new release heading comes before [Unreleased].
    corrupted = (
        "# Changelog\n\n"
        "## \\[1.1.0\\] - 2026-08-21\n\n"
        "### Added\n\n- Added thing one.\n\n"
        "## [Unreleased]\n\n"
        "### Added\n\n### Changed\n\n### Deprecated\n\n"
        "### Removed\n\n### Fixed\n\n### Security\n\n"
    ) + SAMPLE_CHANGELOG[SAMPLE_CHANGELOG.index("## \\[1.0.5\\]") :]
    with pytest.raises(PrepareReleaseError, match="precede"):
        changelog.assert_changelog_structure(
            original_text=SAMPLE_CHANGELOG, new_text=corrupted, version="1.1.0"
        )


def test_extract_released_section() -> None:
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-21"
    )
    section = changelog.extract_released_section(changelog_text=promoted, version="1.1.0")
    assert "Added thing one" in section
    assert "1.0.5" not in section


def test_parse_unreleased_sections() -> None:
    sections = changelog._parse_unreleased_sections(SAMPLE_CHANGELOG)
    assert list(sections) == list(changelog.SUBSECTIONS)
    assert "Added thing one" in sections["Added"]
    assert "Changed thing one" in sections["Changed"]
    assert sections["Deprecated"].strip() == ""
    assert sections["Removed"].strip() == ""


def test_parse_unreleased_sections__wrong_order_raises() -> None:
    broken = SAMPLE_CHANGELOG.replace(
        "### Added\n\n- Added thing one.\n\n### Changed",
        "### Changed\n\n### Added\n\n- Added thing one.",
    )
    with pytest.raises(PrepareReleaseError):
        changelog._parse_unreleased_sections(broken)


def test_parse_unreleased_sections__no_unreleased_heading_raises() -> None:
    with pytest.raises(PrepareReleaseError):
        changelog._parse_unreleased_sections("# Changelog\n\nnothing here\n")


def test_parse_unreleased_sections__stray_content_before_first_subsection_raises() -> None:
    broken = SAMPLE_CHANGELOG.replace(
        "## [Unreleased]\n\n### Added",
        "## [Unreleased]\n\nSee migration notes below.\n\n### Added",
    )
    with pytest.raises(PrepareReleaseError, match="unexpected content"):
        changelog._parse_unreleased_sections(broken)
