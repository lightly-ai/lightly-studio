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


def test_assert_floor_published():
    dependency.assert_floor_published(
        pyproject_text=SAMPLE_PYPROJECT,
        dependency="lightly-studio-serve",
        published_versions=["0.0.9", "0.1.0", "0.1.1"],
    )


def test_assert_floor_published__equivalent_spelling():
    dependency.assert_floor_published(
        pyproject_text=SAMPLE_PYPROJECT,
        dependency="lightly-studio-serve",
        published_versions=["0.1"],
    )


def test_assert_floor_published__nothing_published():
    with pytest.raises(PrepareReleaseError, match=r"floor of 0\.1\.0, which is not published"):
        dependency.assert_floor_published(
            pyproject_text=SAMPLE_PYPROJECT,
            dependency="lightly-studio-serve",
            published_versions=[],
        )


def test_assert_floor_published__only_later_versions():
    with pytest.raises(PrepareReleaseError, match="not published"):
        dependency.assert_floor_published(
            pyproject_text=SAMPLE_PYPROJECT,
            dependency="lightly-studio-serve",
            published_versions=["0.1.1", "0.2.0"],
        )


def test_assert_floor_published__ignores_versions_it_cannot_compare():
    with pytest.raises(PrepareReleaseError, match="not published"):
        dependency.assert_floor_published(
            pyproject_text=SAMPLE_PYPROJECT,
            dependency="lightly-studio-serve",
            published_versions=["0.1.0.post1", "1!0.1.0"],
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


def test_floor_of():
    assert dependency.floor_of("lightly-studio-serve>=0.1.0,<0.2.0") == "0.1.0"


def test_floor_of__pinned():
    assert dependency.floor_of("lightly-mundig==0.1.15") == "0.1.15"


def test_floor_of__no_lower_bound():
    with pytest.raises(PrepareReleaseError, match="no `>=` or `==` lower bound"):
        dependency.floor_of("lightly-studio-serve<2.0")


def test_admits():
    assert dependency.admits(requirement="foo>=0.1.0,<0.2.0", candidate="0.1.9")


def test_admits__trailing_zeros_are_equal():
    assert dependency.admits(requirement="foo>=0.1", candidate="0.1.0")


def test_admits__pre_release_sorts_below_its_release():
    assert not dependency.admits(requirement="foo>=0.2.0", candidate="0.2.0rc1")
    assert dependency.admits(requirement="foo<0.2.0", candidate="0.2.0rc1")


def test_parse_specifiers():
    assert dependency.parse_specifiers("foo>=0.1.0,<0.2.0") == [(">=", "0.1.0"), ("<", "0.2.0")]


def test_parse_specifiers__no_specifier():
    with pytest.raises(PrepareReleaseError, match="carries no version specifier"):
        dependency.parse_specifiers("lightly-studio-serve")


def test_parse_specifiers__unsupported_operator():
    with pytest.raises(PrepareReleaseError, match="does not implement"):
        dependency.parse_specifiers("foo~=0.1.0")


def test_admits__uncomparable_version():
    with pytest.raises(PrepareReleaseError, match=r"not a plain X\.Y\.Z"):
        dependency.admits(requirement="foo>=0.1.0", candidate="0.1.0.post1")
