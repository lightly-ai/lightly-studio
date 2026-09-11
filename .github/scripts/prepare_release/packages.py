"""The releasable packages of this repository, and where each one's release inputs live.

`lightly-studio` and `lightly-studio-serve` release on their own cadences through the
same three workflows. Everything that differs between the two is here: which
`pyproject.toml` carries the version, which `CHANGELOG.md` the notes come from, what
prefixes the tag so the two version namespaces cannot collide, and what must never
reach the published wheel.

The workflows read this through `package-config`, so a new member is described once
here rather than in three YAML files that then drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from prepare_release.errors import PrepareReleaseError


@dataclass(frozen=True)
class Package:
    """One releasable distribution and the paths the release stages read.

    Attributes:
        distribution: The name on PyPI, and the value of the `package` workflow input.
        display_name: The product name, for the tag message and the release PR body.
        directory: The workspace member directory, relative to the repository root.
        changelog: The changelog to promote, and to take the release notes from.
        tag_prefix: Prefixed to `v<version>` to form the release tag. Empty for
            `lightly-studio`, which keeps the bare `v<version>` namespace it already
            published under.
        needs_node: Whether building the distribution needs Node.js.
        forbidden_dependencies: Substrings that no name in the built wheel's resolved
            dependency tree may contain.
    """

    distribution: str
    display_name: str
    directory: str
    changelog: str
    tag_prefix: str
    needs_node: bool
    forbidden_dependencies: tuple[str, ...] = ()

    @property
    def pyproject(self) -> str:
        """The `pyproject.toml` that carries this package's version."""
        return f"{self.directory}/pyproject.toml"

    @property
    def branch_prefix(self) -> str:
        """Prefixed to `v<version>` to form the release branch name.

        A branch cannot hold the `/` that separates a prefixed tag, so the tag prefix
        is flattened. `lightly-studio` keeps the `release-v<version>` it uses today.
        """
        return "release-" + self.tag_prefix.replace("/", "-")


PACKAGES = (
    Package(
        distribution="lightly-studio",
        display_name="LightlyStudio",
        directory="lightly_studio",
        changelog="CHANGELOG.md",
        tag_prefix="",
        needs_node=True,
    ),
    Package(
        distribution="lightly-studio-serve",
        display_name="LightlyStudio Serve",
        directory="lightly_studio_serve",
        changelog="lightly_studio_serve/CHANGELOG.md",
        tag_prefix="lightly-studio-serve/",
        needs_node=False,
        # Substrings of the normalized name, so one entry covers a whole family.
        forbidden_dependencies=(
            "torch",
            "cuda",
            "nvidia",
            "duckdb",
            "opencv",
            "lightly-studio",
        ),
    ),
)


def get(distribution: str) -> Package:
    """Returns the package published under `distribution`.

    Raises:
        PrepareReleaseError: No package is published under that name.
    """
    for package in PACKAGES:
        if package.distribution == distribution:
            return package
    raise PrepareReleaseError(f"unknown package {distribution!r}, expected one of {_known()}")


def for_tag(tag: str) -> Package:
    """Returns the package a release tag belongs to.

    The longest matching prefix wins, so `lightly-studio-serve/v0.1.1` resolves to the
    serve package rather than to `lightly-studio`, whose prefix is empty.

    Raises:
        PrepareReleaseError: The tag matches no package's `<prefix>v<version>` shape.
    """
    candidates = [package for package in PACKAGES if tag.startswith(f"{package.tag_prefix}v")]
    if not candidates:
        raise PrepareReleaseError(
            f"tag {tag!r} belongs to no known package, expected one of "
            f"{', '.join(f'{p.tag_prefix}v<version>' for p in PACKAGES)}"
        )
    return max(candidates, key=lambda package: len(package.tag_prefix))


def render_config(package: Package) -> str:
    """Renders `package` as the `key=value` lines a workflow step appends to `$GITHUB_OUTPUT`."""
    fields = {
        "distribution": package.distribution,
        "display_name": package.display_name,
        "directory": package.directory,
        "pyproject": package.pyproject,
        "changelog": package.changelog,
        "tag_prefix": package.tag_prefix,
        "branch_prefix": package.branch_prefix,
        "needs_node": str(package.needs_node).lower(),
        "forbidden_dependencies": " ".join(package.forbidden_dependencies),
    }
    return "".join(f"{key}={value}\n" for key, value in fields.items())


def _known() -> str:
    return ", ".join(package.distribution for package in PACKAGES)
