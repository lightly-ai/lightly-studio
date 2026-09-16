# Release

How a merged pull request becomes a published release.

The repository is a [uv workspace](../CONTRIBUTING.md#the-uv-workspace) with two packages,
`lightly-studio` and `lightly-studio-serve`, and each releases on its own: releasing one does not
release the other. Both go through the same three actions.

| Package | Tag |
| --- | --- |
| `lightly-studio` | `vX.Y.Z` |
| `lightly-studio-serve` | `lightly-studio-serve/vX.Y.Z` |

The prefix keeps the two version namespaces from colliding - only `lightly-studio` uses a bare
`vX.Y.Z`.

Release notes are rendered from [CHANGELOG.md](../CHANGELOG.md), or from
[`lightly_studio_serve`'s own](../lightly_studio_serve/CHANGELOG.md) for that package.

## Release process

### 1. Run Prepare Release

Dispatch [Prepare Release](https://github.com/lightly-ai/lightly-studio/actions/workflows/prepare_release.yml) from `main`.

- Pick the `package`.
- Pick the `bump` - `patch`, `minor` or `major`. Nothing is inferred from the changelog. Use
  `version` instead for an explicit version such as a release candidate `1.0.0rc1`.

It promotes the `[Unreleased]` changelog section, bumps the package's `pyproject.toml`, runs
`uv sync` and opens a `Bump version to X.Y.Z` pull request.

### 2. Review and merge the bump pull request

The pull request body carries the draft release notes and a checklist of what to check by hand -
mostly that the notes read as user-facing release notes.

- **Approve the CI run.** The pull request is opened by `github-actions[bot]`, so its checks do not
  start on their own. Use **Approve and run workflows** on the "workflows awaiting approval"
  banner.
- Edit `CHANGELOG.md` on the release branch, not the pull request description. The changelog is
  what gets published.

Merging is the decision to release.

### 3. Draft Release runs on its own

Merging triggers [Draft Release](https://github.com/lightly-ai/lightly-studio/actions/workflows/draft_release.yml), which creates the tag
and a **draft** GitHub release with the notes rendered from the changelog. Edit the notes on the
existing draft if needed.

> **Do not create a release or a tag by hand.** GitHub allows a second release on a tag that
> already has a draft, and warns about nothing. That is how a duplicate release happens.

### 4. Run Finish Release

Dispatch [Finish Release](https://github.com/lightly-ai/lightly-studio/actions/workflows/finish_release.yml) from `main` with the tag from
the draft release and `target` left as `pypi`. It builds the wheel from the tagged commit, uploads
it to PyPI and un-drafts the GitHub release, in that order.

- Dispatch it from `main` - the `pypi` environment is restricted to it and checks the branch the
  run was dispatched from, not the tag being built.
- The run pauses for an approval from `lightly-ai/engineering` before publishing. That is the gate,
  not a hang.
- `target: testpypi` rehearses the same path unattended and leaves the GitHub release a draft, so
  the same tag can then be dispatched again with `target: pypi`.

Done. Check that the release is on PyPI:
[lightly-studio](https://pypi.org/project/lightly-studio/),
[lightly-studio-serve](https://pypi.org/project/lightly-studio-serve/).

> **Release `lightly-studio-serve` before raising LightlyStudio's floor on it.**
> `lightly_studio/pyproject.toml` depends on it, and the workspace source is stripped when the
> wheel is built - so a published LightlyStudio wheel resolves it from PyPI like any other
> dependency. Bumping that floor to a version that is not on PyPI yet produces a LightlyStudio
> release that nobody can install.

## Why there is no separate CI gate on the release commit

Tags are only ever created from `main`: Draft Release triggers on a push to `main`, and its
`workflow_dispatch` retry reaches the same commit. The
`main` branch ruleset (id `9051864`) requires `CI Success Check` and `End2End Success Check`
through an `ALLGREEN` merge queue, with no bypass actors and no force-push, so a commit that can be
tagged has already passed CI. Weakening that ruleset weakens the release, and nothing else will
catch it.

## What if something goes wrong?

Make sure nothing is merged to `main` until the issue is resolved, and say so in
`#dev-studio-discuss`. If something was already merged since the release failed, base fixes on the
release branch rather than `main`, so that code outside the GitHub release is not published.

### Prepare Release failed

It publishes nothing, so there is nothing to roll back. Delete the release branch and its pull
request if they were created, fix the cause and run the action again. The action only automates
what a person can do by hand: promote the changelog, bump the version, run `uv sync`, open the
three-file pull request.

### Finish Release failed

Nothing is live until the upload succeeds, and a draft release can be deleted.

- **Before or during the upload.** Fix the cause and re-dispatch the same tag, unless the bug is in
  the released code itself - see below.
- **After the upload, before the un-draft.** Re-dispatch the same tag: the upload is skipped and
  only the un-draft runs. Do not start a new release for this.
- **A 403 from PyPI** means the Trusted Publisher config did not match the run. It pins repository,
  workflow filename and environment, so a renamed `finish_release.yml`, a dispatch from another
  branch, or a missing publisher entry all look like this.

There is no standing PyPI token and no fallback workflow. If the workflow itself is broken and the
release cannot wait, mint a token scoped to the project, build and `uv publish --token ...` from
the package directory, revoke the token, then re-dispatch Finish Release to un-draft.

### The bug is in published code

Make a pull request with the fix, then start the release process again with a **new version
number**. Never publish code to PyPI that differs from the GitHub release of the same version.

### The bug is in development code

Development code is anything used to build or test LightlyStudio but not shipped in the package - a
Makefile, a build script, the release tooling itself. Which workflow failed decides whether a fix on
`main` is enough.

- **Draft Release** checks its tooling out from `main`, never from the commit it is releasing, and
  it tags the version-bump commit rather than whatever is at the tip of `main`. So merge the fix and
  re-dispatch: the fix takes effect without changing which commit is released.
- **Finish Release** builds the tag's own commit. A bug in that commit's build cannot be fixed by
  merging to `main`, and needs a new version like any shipped bug.

## Internal steps

Deploying the documentation, bumping the self-hosted image, updating the demo deployment and
updating hosted tenants are not part of the OSS release and are not automated here. Lightly
employees: see the internal release runbook.
