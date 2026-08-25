import pytest

from prepare_release import version
from prepare_release.errors import PrepareReleaseError

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
    assert version.current_pyproject_version(SAMPLE_PYPROJECT) == "1.0.5"


def test_current_pyproject_version__missing_raises():
    with pytest.raises(PrepareReleaseError):
        version.current_pyproject_version('[project]\nname = "x"\n')


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("patch", "1.0.6"), ("minor", "1.1.0"), ("major", "2.0.0")],
)
def test_bump_semver(bump, expected):
    assert version.bump_semver("1.0.5", bump) == expected


def test_bump_semver__non_semver_current_version_raises():
    with pytest.raises(PrepareReleaseError):
        version.bump_semver("1.0.0rc1", "patch")


def test_check_labelformat_pin__version_requirement_is_fine():
    version.check_labelformat_pin(SAMPLE_PYPROJECT)


def test_check_labelformat_pin__git_sha_raises():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '"labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"',
    )
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_check_labelformat_pin__single_quoted_git_sha_raises():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        "'labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b'",
    )
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_bump_pyproject_version():
    result = version.bump_pyproject_version(SAMPLE_PYPROJECT, "1.0.6")
    assert 'version = "1.0.6"' in result
    assert 'version = "1.0.5"' not in result
    # Only the [project] version changes, nothing else.
    assert result.replace("1.0.6", "1.0.5") == SAMPLE_PYPROJECT


def test_current_pyproject_version__ignores_version_in_preceding_tool_table():
    text = '[tool.some-plugin]\nversion = "9.9.9"\n\n[project]\nname = "x"\nversion = "1.0.5"\n'
    assert version.current_pyproject_version(text) == "1.0.5"


def test_bump_pyproject_version__ignores_version_in_preceding_tool_table():
    text = '[tool.some-plugin]\nversion = "9.9.9"\n\n[project]\nname = "x"\nversion = "1.0.5"\n'
    result = version.bump_pyproject_version(text, "1.0.6")
    assert 'version = "9.9.9"' in result
    assert 'version = "1.0.6"' in result
    assert 'version = "1.0.5"' not in result


@pytest.mark.parametrize("version_string", ["1.02.3", "01.2.3", "1.2.03"])
def test_bump_semver__leading_zero_component_raises(version_string):
    with pytest.raises(PrepareReleaseError):
        version.bump_semver(version_string, "patch")
