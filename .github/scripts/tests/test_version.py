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
        # A `#` inside a *preceding* entry's URL fragment must not be mistaken
        # for a comment and truncate the labelformat entry off the line.
        pytest.param(
            f'"other @ git+https://x/y.git#subdirectory=other", "labelformat @ {_GIT_PIN}"',
            id="hash_in_preceding_url_fragment",
        ),
    ],
)
def test_check_labelformat_pin__git_sha_raises(replacement):
    text = SAMPLE_PYPROJECT.replace('"labelformat>=0.1.17"', replacement)
    with pytest.raises(PrepareReleaseError, match="git sha"):
        version.check_labelformat_pin(text)


def test_read_project_version():
    assert version.read_project_version(SAMPLE_PYPROJECT) == "1.0.5"


def test_read_project_version__release_candidate():
    assert version.read_project_version('[project]\nversion = "1.0.0rc1"\n') == "1.0.0rc1"


# A `version` in a later table must not be mistaken for the project's own.
def test_read_project_version__ignores_other_tables():
    pyproject = '[project]\nname = "lightly-studio"\n\n[tool.uv]\nversion = "9.9.9"\n'

    with pytest.raises(PrepareReleaseError):
        version.read_project_version(pyproject)


def test_read_project_version__missing_project_table_is_refused():
    with pytest.raises(PrepareReleaseError):
        version.read_project_version('[tool.uv]\nversion = "1.0.0"\n')
