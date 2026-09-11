"""Render the release PR body: the draft release notes plus a reviewer checklist."""

from __future__ import annotations

from prepare_release.packages import Package

_CHECKLIST = """\
- [ ] The notes read as user-facing release notes: no ticket ids (`LIG 1234`), PR numbers or
      internal jargon.
- [ ] Nothing user-visible since the last release is missing.
- [ ] Every entry is under the right heading, and near-duplicate entries are merged into one.
- [ ] The version matches the impact of the entries ([semver](https://semver.org)): minor when
      something notable is added or changed, patch otherwise.
- [ ] CI is green on this branch."""


def render_pr_body(section_body: str, version: str, package: Package) -> str:
    """Assembles the release PR body.

    Args:
        section_body: The changelog section already promoted for this version.
        version: The version being released, e.g. "1.0.6".
        package: The package being released.

    Returns:
        The Markdown body for the release PR.
    """
    return (
        f"Prepares the {package.display_name} {version} release: promotes the `[Unreleased]` "
        f"section of `{package.changelog}`, bumps the version and relocks.\n\n"
        f"## Release notes for {version}\n\n"
        f"Edit `{package.changelog}` on this branch rather than this description - the changelog "
        f"is what gets published, this is a copy of it from when the PR was opened.\n\n"
        f"{section_body}\n\n"
        f"## Review checklist\n\n"
        f"{_guards(package)}\n\n"
        f"{_CHECKLIST}\n\n"
        f"Merging tags this commit and opens a **draft** GitHub release. Nothing is public "
        f"until someone runs Finish Release with `target: pypi`, which builds the wheel, "
        f"publishes it to PyPI and "
        f"un-drafts the release; the docs are still manual.\n"
    )


def _guards(package: Package) -> str:
    """Lists what the workflow already asserted, so the reviewer does not re-check it by hand.

    Keep in sync with prepare_release.yml.
    """
    workspace = "".join(
        f"\n- the requirement on `{name}` admits the version in the tree, and its floor is "
        "published on PyPI,"
        for name in package.workspace_dependencies
    )
    return f"""\
The workflow already checked that:

- exactly `{package.changelog}`, `{package.pyproject}` and `uv.lock` changed,
- the `uv.lock` diff is only this version bump,
- `{package.changelog}` keeps an empty `[Unreleased]` skeleton and every earlier release is \
byte-identical,{workspace}
- Labelformat is pinned by version, not by git sha.

What is left is editorial, and it is what this review is for."""
