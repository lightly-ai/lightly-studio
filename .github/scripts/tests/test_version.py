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


def test_current_pyproject_version__handles_crlf_line_endings():
    text = SAMPLE_PYPROJECT.replace("\n", "\r\n")
    assert version.current_pyproject_version(text) == "1.0.5"


@pytest.mark.parametrize(
    "text",
    [
        '[project]\nname = "x"\nversion="1.0.5"\n',
        '[project]\nname = "x"\n    version = "1.0.5"\n',
    ],
    ids=["no_spaces_around_equals", "indented"],
)
def test_current_pyproject_version__tolerates_non_canonical_spacing(text):
    assert version.current_pyproject_version(text) == "1.0.5"


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("patch", "1.0.6"), ("minor", "1.1.0"), ("major", "2.0.0")],
)
def test_bump_semver(bump, expected):
    assert version.bump_semver("1.0.5", bump) == expected


def test_bump_semver__non_semver_current_version_raises():
    with pytest.raises(PrepareReleaseError):
        version.bump_semver("1.0.0rc1", "patch")


@pytest.mark.parametrize("version_string", ["1.02.3", "01.2.3", "1.2.03"])
def test_bump_semver__leading_zero_component_raises(version_string):
    with pytest.raises(PrepareReleaseError):
        version.bump_semver(version_string, "patch")


def test_bump_semver__trailing_newline_component_raises():
    with pytest.raises(PrepareReleaseError):
        version.bump_semver("1.2.3\n", "patch")


def test_bump_semver__non_ascii_digit_component_raises():
    with pytest.raises(PrepareReleaseError):
        version.bump_semver("1.٢.3", "patch")  # "٢" is the Arabic-Indic digit two


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


def test_check_labelformat_pin__mixed_case_git_sha_raises():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '"LabelFormat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"',
    )
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_check_labelformat_pin__commented_out_example_is_ignored():
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '# - "labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"\n'
        '    "labelformat>=0.1.17"',
    )
    version.check_labelformat_pin(text)


def test_check_labelformat_pin__git_sha_inside_inline_array_raises():
    # A git-pinned entry that isn't the array's first element must still be
    # caught - the check isn't anchored to the start of a line.
    text = (
        '[project]\nname = "x"\nversion = "1.0.5"\n\n'
        'dependencies = ["torch>=2.0", '
        '"labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"]\n'
    )
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_check_labelformat_pin__git_sha_after_plain_entry_raises():
    # A plain entry earlier in the file must not shadow a git-pinned one later.
    text = SAMPLE_PYPROJECT.replace(
        '"labelformat>=0.1.17"',
        '"labelformat>=0.1.17",\n'
        '    "labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"',
    )
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
