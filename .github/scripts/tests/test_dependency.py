import pytest

from prepare_release import dependency
from prepare_release.errors import PrepareReleaseError

SAMPLE_PYPROJECT = """\
[project]
name = "lightly-studio"
version = "1.1.0"
dependencies = [
    "numpy>=1.26.4",
    # "lightly-studio-serve>=9.9.9" is an example, not a requirement.
    "lightly-studio-serve>=0.1.0,<0.2.0",
    "lightly-studio-serve-extras>=5.0",
]
"""


def test_assert_admits_version():
    dependency.assert_admits_version(
        pyproject_text=SAMPLE_PYPROJECT,
        dependency="lightly-studio-serve",
        dependency_version="0.1.1",
    )


def test_assert_admits_version__above_the_cap():
    with pytest.raises(PrepareReleaseError, match="excludes it"):
        dependency.assert_admits_version(
            pyproject_text=SAMPLE_PYPROJECT,
            dependency="lightly-studio-serve",
            dependency_version="0.2.0",
        )


def test_assert_admits_version__below_the_floor():
    with pytest.raises(PrepareReleaseError, match="excludes it"):
        dependency.assert_admits_version(
            pyproject_text=SAMPLE_PYPROJECT,
            dependency="lightly-studio-serve",
            dependency_version="0.0.9",
        )


def test_read_requirement():
    assert (
        dependency.read_requirement(
            pyproject_text=SAMPLE_PYPROJECT, distribution="lightly-studio-serve"
        )
        == "lightly-studio-serve>=0.1.0,<0.2.0"
    )


def test_read_requirement__does_not_match_a_longer_name():
    assert (
        dependency.read_requirement(
            pyproject_text=SAMPLE_PYPROJECT, distribution="lightly-studio-serve-extras"
        )
        == "lightly-studio-serve-extras>=5.0"
    )


def test_read_requirement__missing():
    with pytest.raises(PrepareReleaseError, match="no requirement on 'torch'"):
        dependency.read_requirement(pyproject_text=SAMPLE_PYPROJECT, distribution="torch")


def test_admits():
    assert dependency.admits(requirement="foo>=0.1.0,<0.2.0", candidate="0.1.9")


def test_admits__pre_release_of_the_cap_is_excluded():
    # PEP 440: an exclusive `<V` excludes pre-releases of V too, so a release
    # candidate for the cap needs the cap widened just as the release does.
    assert not dependency.admits(requirement="foo>=0.1.0,<0.2.0", candidate="0.2.0rc1")


def test_admits__no_specifier():
    with pytest.raises(PrepareReleaseError, match="carries no version specifier"):
        dependency.admits(requirement="lightly-studio-serve", candidate="0.1.0")


def test_admits__invalid_requirement():
    with pytest.raises(PrepareReleaseError, match="not valid PEP 508"):
        dependency.admits(requirement="foo>=>=0.1.0", candidate="0.1.0")


def test_admits__invalid_candidate():
    with pytest.raises(PrepareReleaseError, match="not valid PEP 440"):
        dependency.admits(requirement="foo>=0.1.0", candidate="not-a-version")
