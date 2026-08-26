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


def test_current_pyproject_version__ignores_version_in_preceding_tool_table():
    text = '[tool.some-plugin]\nversion = "9.9.9"\n\n[project]\nname = "x"\nversion = "1.0.5"\n'
    assert version.current_pyproject_version(text) == "1.0.5"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(SAMPLE_PYPROJECT.replace("\n", "\r\n"), id="crlf"),
        pytest.param('[project]\nname = "x"\nversion="1.0.5"\n', id="no_spaces_around_equals"),
        pytest.param('[project]\nname = "x"\n    version = "1.0.5"\n', id="indented"),
    ],
)
def test_current_pyproject_version__tolerates_format_variations(text):
    assert version.current_pyproject_version(text) == "1.0.5"


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("patch", "1.0.6"), ("minor", "1.1.0"), ("major", "2.0.0")],
)
def test_bump_semver(bump, expected):
    assert version.bump_semver("1.0.5", bump) == expected


@pytest.mark.parametrize(
    "version_string",
    [
        pytest.param("1.0.0rc1", id="not_plain_semver"),
        pytest.param("1.02.3", id="leading_zero"),
        pytest.param("01.2.3", id="leading_zero_major"),
        pytest.param("1.2.03", id="leading_zero_patch"),
        pytest.param("1.2.3\n", id="trailing_newline"),
        pytest.param("1.٢.3", id="non_ascii_digit"),  # "٢" is the Arabic-Indic digit two
    ],
)
def test_bump_semver__invalid_version_raises(version_string):
    with pytest.raises(PrepareReleaseError):
        version.bump_semver(version_string, "patch")


def test_check_labelformat_pin__version_requirement_is_fine():
    version.check_labelformat_pin(SAMPLE_PYPROJECT)


def test_check_labelformat_pin__commented_out_example_is_ignored():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '# - "labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"\n'
        '    "labelformat>=0.1.17"',
    )
    version.check_labelformat_pin(text)


_GIT_PIN = "git+https://github.com/lightly-ai/labelformat.git@325a20b"


@pytest.mark.parametrize(
    "replacement",
    [
        pytest.param(f'"labelformat @ {_GIT_PIN}"', id="double_quoted"),
        pytest.param(f"'labelformat @ {_GIT_PIN}'", id="single_quoted"),
        pytest.param(f'"LabelFormat @ {_GIT_PIN}"', id="mixed_case"),
        # Not the array's first (or only) entry on its line - the check
        # must not stop at the first match, nor anchor to a line's start.
        pytest.param(f'"labelformat>=0.1.17", "labelformat @ {_GIT_PIN}"', id="after_plain_entry"),
    ],
)
def test_check_labelformat_pin__git_sha_raises(replacement):
    text = SAMPLE_PYPROJECT.replace('"labelformat>=0.1.17"', replacement)
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_bump_pyproject_version():
    result = version.bump_pyproject_version(SAMPLE_PYPROJECT, "1.0.6")
    assert 'version = "1.0.6"' in result
    assert 'version = "1.0.5"' not in result
    # Only the [project] version changes, nothing else.
    assert result.replace("1.0.6", "1.0.5") == SAMPLE_PYPROJECT


def test_bump_pyproject_version__ignores_version_in_preceding_tool_table():
    text = '[tool.some-plugin]\nversion = "9.9.9"\n\n[project]\nname = "x"\nversion = "1.0.5"\n'
    result = version.bump_pyproject_version(text, "1.0.6")
    assert 'version = "9.9.9"' in result
    assert 'version = "1.0.6"' in result
    assert 'version = "1.0.5"' not in result


def test_bump_pyproject_version__preserves_crlf_line_endings():
    text = SAMPLE_PYPROJECT.replace("\n", "\r\n")
    result = version.bump_pyproject_version(text, "1.0.6")
    assert 'version = "1.0.6"\r\n' in result
    assert result.replace("1.0.6", "1.0.5") == text


def test_bump_pyproject_version__tolerates_no_spaces_around_equals():
    text = '[project]\nname = "x"\nversion="1.0.5"\n'
    result = version.bump_pyproject_version(text, "1.0.6")
    assert 'version = "1.0.6"' in result
    assert "1.0.5" not in result
