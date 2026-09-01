# Check release CI

Fails unless every required CI check succeeded on the **exact commit** being
released. Release workflows call it before tagging, publishing a wheel or
deploying docs.

```yaml
- uses: lightly-ai/lightly-studio/.github/actions/check-release-ci@main
  with:
    ref: v1.2.3            # tag, branch or sha being released
    github-token: ${{ github.token }}
```

GitHub checks out this whole repository for the action, so the gate in
`.github/scripts` comes along and cross-repo callers - including the private
repo's docs workflow - need nothing else. The runner needs `gh` and `python3`,
and the job needs `checks: read`.

Set `skip-ci-check: true` for the documented emergency path. It skips the gate
and records the override, with the actor's name, in the job summary.

## What counts as green

The rules and their reasoning live in
[`ci_gate.py`](../../scripts/prepare_release/ci_gate.py). `main` is green by
construction - the merge queue tests the squashed candidate - so on the normal
path this gate is a no-op. It is here for the paths that skip the queue: a fix
released from a release branch, the docs release accepting an arbitrary commit,
and above all automated publishing, where nothing else is looking at CI.

## Verified against

A gate that returns success unconditionally also passes a green commit, so the
red cases decide. `unit_test.yml` re-runs the first and last row on every change
to the gate; re-check the rest by hand after changing it.

| Case | Commit | Expected |
| --- | --- | --- |
| Both required checks failed | `1f9b2156d23ecf5033b1cfe34be06af5d903d83c` | blocks, naming both |
| One required check failed | `a311e602b9fadd5c4e950adde7786aa53bc6fa5c` | blocks, naming `CI Success Check` |
| Every gated unit-test job `skipped`, aggregate green | `da604e0802b9f91adf9ac8cca298623a587c62e1` | passes |
| Green, with a cancelled push attempt | `2ae55628ff29e01065d748128d7a39aa4519f8bf` | passes, flagging the other attempt |
| Green | `b2dc2470d5a0055e791944dbd14a4e965ff615bd` | passes |

Checks still running was verified live rather than against a fixed sha, since
any commit goes green afterwards: run against `0b6cfbc8` mid-flight, the gate
refused it. An aggregate job gets no check run until the jobs it waits on
finish, so this arrives as an absent check rather than a running one.
