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


def test_parse_unreleased_sections():
    sections = changelog.parse_unreleased_sections(SAMPLE_CHANGELOG)
    assert list(sections) == list(changelog.SUBSECTIONS)
    assert "Added thing one" in sections["Added"]
    assert "Changed thing one" in sections["Changed"]
    assert sections["Deprecated"].strip() == ""
    assert sections["Removed"].strip() == ""


def test_parse_unreleased_sections__wrong_order_raises():
    broken = SAMPLE_CHANGELOG.replace(
        "### Added\n\n- Added thing one.\n\n### Changed",
        "### Changed\n\n### Added\n\n- Added thing one.",
    )
    with pytest.raises(PrepareReleaseError):
        changelog.parse_unreleased_sections(broken)


def test_parse_unreleased_sections__no_unreleased_heading_raises():
    with pytest.raises(PrepareReleaseError):
        changelog.parse_unreleased_sections("# Changelog\n\nnothing here\n")


def test_suggest_bump__added_or_changed_suggests_minor():
    sections = changelog.parse_unreleased_sections(SAMPLE_CHANGELOG)
    bump, reasoning = changelog.suggest_bump(sections)
    assert bump == "minor"
    assert "Added" in reasoning
    assert "Changed" in reasoning


def test_suggest_bump__only_fixed_or_security_suggests_patch():
    sections = dict.fromkeys(changelog.SUBSECTIONS, "")
    sections["Fixed"] = "- Fixed a bug.\n"
    bump, _ = changelog.suggest_bump(sections)
    assert bump == "patch"


def test_suggest_bump__nothing_unreleased_raises():
    sections = dict.fromkeys(changelog.SUBSECTIONS, "")
    with pytest.raises(PrepareReleaseError, match="nothing to release"):
        changelog.suggest_bump(sections)


def test_promote_changelog():
    promoted = changelog.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")

    # Fresh, fully-empty [Unreleased] skeleton with all six subheadings.
    assert promoted.count("## [Unreleased]") == 1
    for name in changelog.SUBSECTIONS:
        assert f"### {name}\n\n" in promoted

    # New release heading in escaped form, empty sections dropped.
    assert "## \\[1.1.0\\] - 2026-08-21" in promoted
    assert "Added thing one" in promoted
    assert "Changed thing one" in promoted

    # Previously-released blocks are untouched.
    assert "## \\[1.0.5\\] - 2026-08-14" in promoted
    assert "## \\[1.0.4\\] - 2026-08-01" in promoted
    assert promoted.index("1.1.0") < promoted.index("1.0.5") < promoted.index("1.0.4")

    changelog.assert_changelog_structure(SAMPLE_CHANGELOG, promoted, "1.1.0")


def test_assert_changelog_structure__missing_unreleased_raises():
    promoted = changelog.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("## [Unreleased]\n\n", "", 1)
    with pytest.raises(PrepareReleaseError):
        changelog.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_assert_changelog_structure__mutated_released_block_raises():
    promoted = changelog.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("An older fix.", "A DIFFERENT fix.")
    with pytest.raises(PrepareReleaseError, match="byte-identical"):
        changelog.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_assert_changelog_structure__missing_new_heading_raises():
    promoted = changelog.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("## \\[1.1.0\\] - 2026-08-21", "## [1.1.0] - 2026-08-21")
    with pytest.raises(PrepareReleaseError):
        changelog.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_extract_released_section():
    promoted = changelog.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    section = changelog.extract_released_section(promoted, "1.1.0")
    assert "Added thing one" in section
    assert "1.0.5" not in section
