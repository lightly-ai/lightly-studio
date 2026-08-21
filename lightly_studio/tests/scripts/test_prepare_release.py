import prepare_release
import pytest
from prepare_release import PrepareReleaseError

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

SAMPLE_PYPROJECT = """\
[project]
name = "lightly-studio"
version = "1.0.5"
description = "..."

dependencies = [
    "labelformat>=0.1.17",
]
"""


def test_current_pyproject_version():
    assert prepare_release.current_pyproject_version(SAMPLE_PYPROJECT) == "1.0.5"


def test_current_pyproject_version__missing_raises():
    with pytest.raises(PrepareReleaseError):
        prepare_release.current_pyproject_version('[project]\nname = "x"\n')


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("patch", "1.0.6"), ("minor", "1.1.0"), ("major", "2.0.0")],
)
def test_bump_semver(bump, expected):
    assert prepare_release.bump_semver("1.0.5", bump) == expected


def test_bump_semver__non_semver_current_version_raises():
    with pytest.raises(PrepareReleaseError):
        prepare_release.bump_semver("1.0.0rc1", "patch")


def test_check_labelformat_pin__version_requirement_is_fine():
    prepare_release.check_labelformat_pin(SAMPLE_PYPROJECT)


def test_check_labelformat_pin__git_sha_raises():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '"labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"',
    )
    with pytest.raises(PrepareReleaseError, match="git sha"):
        prepare_release.check_labelformat_pin(text)


def test_bump_pyproject_version():
    result = prepare_release.bump_pyproject_version(SAMPLE_PYPROJECT, "1.0.6")
    assert 'version = "1.0.6"' in result
    assert 'version = "1.0.5"' not in result
    # Only the [project] version changes, nothing else.
    assert result.replace("1.0.6", "1.0.5") == SAMPLE_PYPROJECT


def test_parse_unreleased_sections():
    sections = prepare_release.parse_unreleased_sections(SAMPLE_CHANGELOG)
    assert list(sections) == list(prepare_release.SUBSECTIONS)
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
        prepare_release.parse_unreleased_sections(broken)


def test_parse_unreleased_sections__no_unreleased_heading_raises():
    with pytest.raises(PrepareReleaseError):
        prepare_release.parse_unreleased_sections("# Changelog\n\nnothing here\n")


def test_suggest_bump__added_or_changed_suggests_minor():
    sections = prepare_release.parse_unreleased_sections(SAMPLE_CHANGELOG)
    bump, reasoning = prepare_release.suggest_bump(sections)
    assert bump == "minor"
    assert "Added" in reasoning
    assert "Changed" in reasoning


def test_suggest_bump__only_fixed_or_security_suggests_patch():
    sections = dict.fromkeys(prepare_release.SUBSECTIONS, "")
    sections["Fixed"] = "- Fixed a bug.\n"
    bump, _ = prepare_release.suggest_bump(sections)
    assert bump == "patch"


def test_suggest_bump__nothing_unreleased_raises():
    sections = dict.fromkeys(prepare_release.SUBSECTIONS, "")
    with pytest.raises(PrepareReleaseError, match="nothing to release"):
        prepare_release.suggest_bump(sections)


def test_promote_changelog():
    promoted = prepare_release.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")

    # Fresh, fully-empty [Unreleased] skeleton with all six subheadings.
    assert promoted.count("## [Unreleased]") == 1
    for name in prepare_release.SUBSECTIONS:
        assert f"### {name}\n\n" in promoted

    # New release heading in escaped form, empty sections dropped.
    assert "## \\[1.1.0\\] - 2026-08-21" in promoted
    assert "Added thing one" in promoted
    assert "Changed thing one" in promoted

    # Previously-released blocks are untouched.
    assert "## \\[1.0.5\\] - 2026-08-14" in promoted
    assert "## \\[1.0.4\\] - 2026-08-01" in promoted
    assert promoted.index("1.1.0") < promoted.index("1.0.5") < promoted.index("1.0.4")

    prepare_release.assert_changelog_structure(SAMPLE_CHANGELOG, promoted, "1.1.0")


def test_assert_changelog_structure__missing_unreleased_raises():
    promoted = prepare_release.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("## [Unreleased]\n\n", "", 1)
    with pytest.raises(PrepareReleaseError):
        prepare_release.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_assert_changelog_structure__mutated_released_block_raises():
    promoted = prepare_release.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("An older fix.", "A DIFFERENT fix.")
    with pytest.raises(PrepareReleaseError, match="byte-identical"):
        prepare_release.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_assert_changelog_structure__missing_new_heading_raises():
    promoted = prepare_release.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    corrupted = promoted.replace("## \\[1.1.0\\] - 2026-08-21", "## [1.1.0] - 2026-08-21")
    with pytest.raises(PrepareReleaseError):
        prepare_release.assert_changelog_structure(SAMPLE_CHANGELOG, corrupted, "1.1.0")


def test_extract_released_section():
    promoted = prepare_release.promote_changelog(SAMPLE_CHANGELOG, "1.1.0", "2026-08-21")
    section = prepare_release.extract_released_section(promoted, "1.1.0")
    assert "Added thing one" in section
    assert "1.0.5" not in section


def test_render_pr_body():
    body = prepare_release.render_pr_body(
        section_body="### Added\n\n- Added thing one.",
        drafting_skipped_reason="LIG-10559 is not wired in yet",
        coverage_checklist="- abc123 Some PR title (#42)",
    )
    assert "Draft release notes" in body
    assert "LIG-10559 is not wired in yet" in body
    assert "Added thing one" in body
    assert "Coverage checklist" in body
    assert "#42" in body


def test_render_pr_body__empty_checklist_shows_placeholder():
    body = prepare_release.render_pr_body(
        section_body="### Fixed\n\n- A fix.",
        drafting_skipped_reason="reason",
        coverage_checklist="",
    )
    assert "_None found._" in body


SAMPLE_LOCK = """\
version = 1
revision = 2

[[package]]
name = "alpha"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "lightly-studio"
version = "1.0.5"
source = { editable = "." }
dependencies = [
    { name = "alpha" },
]
"""


def test_parse_lock_blocks():
    blocks = prepare_release.parse_lock_blocks(SAMPLE_LOCK)
    assert set(blocks) == {"", "alpha", "lightly-studio"}
    assert 'version = "1.0.5"' in blocks["lightly-studio"]


def test_assert_lock_diff_narrow__version_only_change_is_ok():
    after = SAMPLE_LOCK.replace(
        'name = "lightly-studio"\nversion = "1.0.5"', 'name = "lightly-studio"\nversion = "1.0.6"'
    )
    prepare_release.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")


def test_assert_lock_diff_narrow__unrelated_package_changed_raises():
    after = SAMPLE_LOCK.replace(
        'name = "alpha"\nversion = "1.0.0"', 'name = "alpha"\nversion = "1.1.0"'
    )
    with pytest.raises(PrepareReleaseError, match="alpha"):
        prepare_release.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")


def test_assert_lock_diff_narrow__broader_change_to_target_package_raises():
    after = SAMPLE_LOCK.replace(
        'version = "1.0.5"\nsource = { editable = "." }',
        'version = "1.0.6"\nsource = { editable = "./elsewhere" }',
    )
    with pytest.raises(PrepareReleaseError, match="more than its version line"):
        prepare_release.assert_lock_diff_narrow(SAMPLE_LOCK, after, package="lightly-studio")
