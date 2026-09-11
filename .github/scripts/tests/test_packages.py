import pytest

from prepare_release import packages
from prepare_release.errors import PrepareReleaseError

SERVE = packages.get("lightly-studio-serve")
STUDIO = packages.get("lightly-studio")


class TestPackage:
    def test_pyproject(self):
        assert STUDIO.pyproject == "lightly_studio/pyproject.toml"

    def test_branch_prefix(self):
        assert STUDIO.branch_prefix == "release-"

    def test_branch_prefix__prefixed_package_flattens_the_slash(self):
        assert SERVE.branch_prefix == "release-lightly-studio-serve-"


def test_get():
    assert packages.get("lightly-studio").directory == "lightly_studio"


def test_get__unknown():
    with pytest.raises(PrepareReleaseError, match="unknown package 'lightly-train'"):
        packages.get("lightly-train")


def test_for_tag():
    assert packages.for_tag("v1.2.3") is STUDIO


def test_for_tag__longest_prefix_wins():
    assert packages.for_tag("lightly-studio-serve/v0.1.2") is SERVE


def test_for_tag__unknown():
    with pytest.raises(PrepareReleaseError, match="belongs to no known package"):
        packages.for_tag("nightly/v1.2.3")


def test_for_tag__no_version_marker():
    with pytest.raises(PrepareReleaseError, match="belongs to no known package"):
        packages.for_tag("1.2.3")


def test_render_config():
    assert packages.render_config(STUDIO) == (
        "distribution=lightly-studio\n"
        "display_name=LightlyStudio\n"
        "directory=lightly_studio\n"
        "pyproject=lightly_studio/pyproject.toml\n"
        "changelog=CHANGELOG.md\n"
        "tag_prefix=\n"
        "branch_prefix=release-\n"
        "needs_node=true\n"
        "forbidden_dependencies=\n"
        "workspace_dependencies=lightly-studio-serve\n"
    )


def test_render_config__serve():
    assert packages.render_config(SERVE) == (
        "distribution=lightly-studio-serve\n"
        "display_name=LightlyStudio Serve\n"
        "directory=lightly_studio_serve\n"
        "pyproject=lightly_studio_serve/pyproject.toml\n"
        "changelog=lightly_studio_serve/CHANGELOG.md\n"
        "tag_prefix=lightly-studio-serve/\n"
        "branch_prefix=release-lightly-studio-serve-\n"
        "needs_node=false\n"
        "forbidden_dependencies=torch cuda nvidia duckdb opencv lightly-studio\n"
        "workspace_dependencies=\n"
    )


def test_tags_cannot_collide():
    tags = [f"{package.tag_prefix}v1.2.3" for package in packages.PACKAGES]
    assert len(set(tags)) == len(tags)
