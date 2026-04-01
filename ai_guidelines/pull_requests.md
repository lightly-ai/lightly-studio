# Pull Request Guidelines

Break changes down into small, focused pull requests that can be easily reviewed.
As a rule of thumb, a PR should be reviewable in under 15 minutes.

## Guidelines

### 1. Keep PRs Small

- Ideal PR size is under 100 changed lines. Under 200 lines is usually acceptable. Larger
  changes should be split into multiple PRs unless there is a reason not to.
- It is ok to have a larger PR if it is mostly mechanical changes, such as generated files, test
  data, or formatting. But the core PR logic should still be ideally under 100 lines.
- Use stacked PRs to work on larger features without being blocked by review.

### 2. One Purpose Per PR

- A pull request should do one thing only. Do not mix unrelated changes in the same PR.
- Minor improvements to the neighborhood of the main change are ok, but larger refactors
  should be in a separate PR.

### 3. Every PR Must Be Reviewable on Its Own

A reviewer should be able to understand what changed, why, and how it was validated. That usually
means:

- In the code
   - clear comments for non-obvious logic
   - TODO comments for future work
   - tests for new behavior when appropriate
   - updated docs when user-facing behavior changed
   - no unrelated formatting or cleanup noise
- In the PR on GitHub
   - clear PR description
   - screenshots or recordings for UI changes
   - line comments for non-obvious code changes

In some some cases, the tests or a docs change may be in a separate PR if it would be too large to
review together.

## Exceptions

Some PRs will not fit the normal shape. Examples:

- dependency upgrades
- mechanical codemods
- large test updates
- schema or migration changes
- generated files

In those cases, optimize for reviewer clarity:

- explain why the PR is large
- separate mechanical and logical changes where possible
- call out risk areas explicitly
