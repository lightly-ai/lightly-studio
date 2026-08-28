# Check release CI

Fails unless every required CI check succeeded on the **exact commit** being
released. Release workflows call it before tagging, publishing a wheel or
deploying docs, so a release is never cut from an untested or red commit.

## Why the release PR's own CI is not enough

The version-bump PR runs Unit Test and End2End Test, but a release is published
from a ref, and that ref is not necessarily the commit those runs tested:

- Squash-merging the release PR produces a **new** commit on `main`. The PR's
  runs belong to the PR head, not to what was merged.
- `workflow_dispatch` puts no ordering between "merge" and "publish". A publish
  can be dispatched while `main`'s runs are still going, or after they failed.
- `RELEASE.md`'s emergency path releases from a release branch, which may have
  no runs at all.

The gate closes the gap by asking about the sha rather than about the branch.

## Usage

```yaml
- uses: lightly-ai/lightly-studio/.github/actions/check-release-ci@main
  with:
    ref: v1.2.3            # tag, branch or sha being released
    github-token: ${{ github.token }}
```

Cross-repo callers - including the private repo's docs workflow - use the
action as above. Workflows in this repository can instead call the job wrapper
`.github/workflows/check_release_ci.yml`, which also exposes the gate as a
`workflow_dispatch` for manual checks. The runner needs `gh` and `python3`.

Set `skip-ci-check: true` for the documented emergency path. It skips the gate
entirely and records the override, with the actor's name, in the log and the
job summary.

## What counts as green

The required checks are named once, in `REQUIRED_CHECKS` in
[`.github/scripts/prepare_release/ci_gate.py`](../../scripts/prepare_release/ci_gate.py),
which also carries the reasoning. In short:

- The required names are the two **aggregate jobs**, `CI Success Check` and
  `End2End Success Check` - not the workflow names `Unit Test` and `End2End
  Test`, which name no check run and would pass vacuously.
- Only a completed `success` counts. Missing, still running, `cancelled`,
  `skipped` and `neutral` all block.
- One completed green attempt on the sha is enough, because a commit on `main`
  carries each check twice and `cancel-in-progress: true` routinely cancels the
  push-to-main attempt. Other attempts are reported next to the green one.

## Verified against

A gate that returns success unconditionally also passes on a green commit, so
these were checked in this order. Re-run them after changing the gate:

| Case | Commit | Expected | Result |
| --- | --- | --- | --- |
| Both required checks failed | `1f9b2156d23ecf5033b1cfe34be06af5d903d83c` | blocks, naming both | blocks, both named and linked |
| One required check failed | `a311e602b9fadd5c4e950adde7786aa53bc6fa5c` | blocks, naming `CI Success Check` | blocks, named and linked |
| Every gated unit-test job `skipped`, aggregate green | `da604e0802b9f91adf9ac8cca298623a587c62e1` | passes - the aggregate resolves its own skipped jobs | passes |
| Green, with a cancelled push attempt | `2ae55628ff29e01065d748128d7a39aa4519f8bf` | passes, flagging the other attempt | passes, flagged |
| Green | `b2dc2470d5a0055e791944dbd14a4e965ff615bd` | passes | passes |

Checks still running was verified live rather than against a fixed sha, since
any commit goes green afterwards: run against `0b6cfbc8` while its CI was in
flight, the gate refused it with "is not reported yet; 12 check(s) on this
commit are still running". An aggregate job gets no check run until the jobs it
waits on finish, so this case arrives as an absent check rather than a running
one - which is why it is worth stating separately from a commit that was never
tested at all.

The still-running and misspelled-requirement cases are also unit tested in
`.github/scripts/tests/test_ci_gate.py`, which pins `skipped` as blocking when a
required check itself reports it.
