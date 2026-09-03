"""Render the release PR body: the draft release notes plus a reviewer checklist."""

from __future__ import annotations

# What the workflow already asserted before opening the PR, so the reviewer does
# not re-check it by hand. Keep in sync with prepare_release.yml.
_GUARDS = """\
The workflow already checked that:

- exactly `CHANGELOG.md`, `lightly_studio/pyproject.toml` and `lightly_studio/uv.lock` changed,
- the `uv.lock` diff is only this version bump,
- `CHANGELOG.md` keeps an empty `[Unreleased]` skeleton and every earlier release is byte-identical,
- Labelformat is pinned by version, not by git sha.

What is left is editorial, and it is what this review is for."""

_CHECKLIST = """\
- [ ] The notes read as user-facing release notes: no ticket ids (`LIG 1234`), PR numbers or
      internal jargon.
- [ ] Nothing user-visible since the last release is missing.
- [ ] Every entry is under the right heading, and near-duplicate entries are merged into one.
- [ ] The version matches the impact of the entries ([semver](https://semver.org)): minor when
      something notable is added or changed, patch otherwise.
- [ ] CI is green on this branch."""


def render_pr_body(section_body: str, version: str) -> str:
    """Assembles the release PR body.

    Args:
        section_body: The CHANGELOG section already promoted for this version.
        version: The version being released, e.g. "1.0.6".

    Returns:
        The Markdown body for the release PR.
    """
    return (
        f"Prepares the LightlyStudio {version} release: promotes the `[Unreleased]` changelog "
        f"section, bumps the version and relocks.\n\n"
        f"## Release notes for {version}\n\n"
        f"Edit `CHANGELOG.md` on this branch rather than this description - the changelog is what "
        f"gets published, this is a copy of it from when the PR was opened.\n\n"
        f"{section_body}\n\n"
        f"## Review checklist\n\n"
        f"{_GUARDS}\n\n"
        f"{_CHECKLIST}\n\n"
        f"Merging tags this commit and opens a **draft** GitHub release. Nothing is public "
        f"until the wheel is on PyPI and someone runs Undraft Release; PyPI and the docs are "
        f"still manual.\n"
    )
