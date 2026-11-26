---
name: prepare-release-changelog
description: Use when reviewing or editing the changelog of a release before it is merged, for example on a "Bump lightly-studio version to X.Y.Z" pull request, or when asked to make the release notes human-readable, find missing entries, or remove duplicates.
---

# Prepare the Release Changelog

The release section of `CHANGELOG.md` becomes the GitHub release notes. Between releases,
AI agents add one entry per pull request. Before the release, the section must read as one
set of notes for a LightlyStudio user.

Load the `changelog` skill first. Its rules apply to each entry. This skill applies to the
section as a whole.

## Scope

- Edit only the new release section, for example `## \[1.5.0\] - 2026-11-26`.
- Keep the `## [Unreleased]` skeleton and the earlier releases byte-identical. The release
  workflow fails if they change.
- For `lightly-studio-serve`, use `lightly_studio_serve/CHANGELOG.md` and its own tags
  (`lightly-studio-serve/vX.Y.Z`).

## Steps

1. **Read the style reference.** Read the last three releases in `CHANGELOG.md`. Match
   their grouping, group names, and wording.

2. **Ask which features are not released.** Some features are merged but hidden, or are
   for one customer only. Earlier examples: MCAP and point cloud features in 1.3.0. Ask
   the user which features to leave out. Do not guess from the code.

3. **Remove internal entries:**
   - internal changes: refactors, tests, CI, silent dependency bumps, log messages,
   - features from step 2,
   - ticket ids (`LIG-1234`), PR numbers, and code names.

4. **Find missing entries.** List the commits since the previous release:

   ```
   git log v<previous>..HEAD --no-merges --format='%h %s'
   ```

   Read every commit, not only `feat:` and `fix:` ones: many user-facing commits have no
   prefix, for example "Delete annotation sources in Settings". Skip `refactor:`, `test:`,
   `ci:`, `chore:`, and `build:` commits.

   For each user-facing commit, check that an entry covers it. When the title is not
   clear, read the pull request description with `gh pr view <number>`. Add an entry for
   each gap, and list the commit in the report.

5. **Fix headings and merge duplicates.** Move each entry under the correct heading:
   Added, Changed, Deprecated, Removed, Fixed, or Security. Several pull requests often
   build one feature. Merge their entries into one that describes the result. Example:
   three entries about the brightness, contrast, and mask-opacity sliders become one.

6. **Group the entries.** When a heading has more than four entries, group them by
   product area. Reuse group names from earlier releases: Annotations, Labeling,
   Filtering, Video queries, Sample details, Embedding plot, Point clouds, Evaluation and
   export, Documentation. Put "Other" last. Put the most important groups and entries
   first.

7. **Check the wording.** Apply the `changelog` skill: what the user can now do, one or two
   short sentences, `Python SDK:` and `BREAKING:` prefixes, the one step a breaking change
   needs. Keep a `BREAKING:` entry under its heading, at the top of its group.

8. **Check the version.** Minor for notable changes, otherwise patch. A `BREAKING:` entry
   does not force a major version before 2.0, but say it in the report.

## Format

Match the previous releases exactly:

```markdown
### Added

- Filtering
    - Reapply any of the last 10 queries used in a collection from the query history.
    - Search any filter list, select all its values, or clear the selection.

- Labeling
    - Choose an annotation source in the Annotations panel when labeling images.

### Removed

- BREAKING: LightlyStudio no longer supports Python 3.10. Upgrade to Python 3.11–3.15 before installing this release.
```

- Group names are plain text, not bold, with no colon.
- Indent entries under a group with four spaces.
- One blank line between groups. No blank lines between entries.
- Remove empty headings, such as `### Security` with no entries.
- Keep the escaped version heading (`## \[1.5.0\]`) as it is.

## Report

After the edit, report to the user:

- removed entries, and why,
- merged entries,
- added entries, each with its commit,
- the version check,
- questions you could not answer, such as a feature you are not sure is released.

Do not commit or push unless the user asks.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Keep every PR's entry | Each entry must be useful to a user. Remove internal ones. |
| Describe each PR of a feature | Describe the final feature once. |
| List hidden or customer-only features | Ask the user in step 2. |
| Edit the PR description | Edit `CHANGELOG.md` on the release branch. The changelog is published. |
| Reformat earlier releases | Edit only the new section. |

## Improve this skill

If this skill did not work as it should, for example a step failed or misled you, a step was
missing, or the user corrected a step, briefly suggest a fix at the end of your final reply.
If the skill worked, say nothing.
