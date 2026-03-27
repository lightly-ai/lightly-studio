# Pull Requests guidelines


## Atomic Pull Requests

Creating small, focused pull requests is crucial for maintainability, code review quality, and reducing the risk of bugs. Follow these principles to keep PRs atomic and reviewable.

### Size Guidelines

**Golden Rule: Keep PRs under 300 lines of changes**

- **Small PRs (< 100 lines):** Ideal for bug fixes, small features, and documentation updates
- **Medium PRs (100-300 lines):** Acceptable for feature additions with proper splitting
- **Large PRs (> 300 lines):** Should be split into multiple smaller PRs

**Why 300 lines?**

- Takes ~30 minutes to review thoroughly
- Easier to spot bugs and issues
- Faster to merge and deploy
- Reduces merge conflicts
- Easier to revert if needed

### Splitting Large Features

When implementing a large feature, split it into a logical progression of PRs:

#### Strategy 1: Bottom-Up Approach (Recommended)

Build from the foundation up, introducing components and utilities before their usage:

```
PR 1: Add utility functions and types
PR 2: Add reusable hooks (useFileUpload)
PR 3: Add component-specific hooks (useImageUploadHandlers)
PR 4: Add leaf components (SearchInput, ActiveSearchDisplay)
PR 5: Add parent component (GridSearch)
PR 6: Integrate component into existing pages
PR 7: Add documentation and examples
```

**Example: Adding Image Search Feature**

```
✅ PR 1 (150 lines): Add useFileUpload hook + tests
   - src/lib/hooks/useFileUpload/useFileUpload.ts
   - src/lib/hooks/useFileUpload/useFileUpload.test.ts

✅ PR 2 (120 lines): Add useImageUploadHandlers hook + tests
   - src/lib/components/GridSearch/hooks/useImageUploadHandlers/useImageUploadHandlers.ts
   - src/lib/components/GridSearch/hooks/useImageUploadHandlers/useImageUploadHandlers.test.ts

✅ PR 3 (180 lines): Add SearchInput and ActiveSearchDisplay components
   - src/lib/components/GridSearch/SearchInput/SearchInput.svelte
   - src/lib/components/GridSearch/SearchInput/SearchInput.test.ts
   - src/lib/components/GridSearch/ActiveSearchDisplay/ActiveSearchDisplay.svelte
   - src/lib/components/GridSearch/ActiveSearchDisplay/ActiveSearchDisplay.test.ts

✅ PR 4 (150 lines): Add GridSearch orchestrator component
   - src/lib/components/GridSearch/GridSearch.svelte
   - src/lib/components/GridSearch/GridSearch.test.ts

✅ PR 5 (80 lines): Integrate GridSearch into collection page
   - src/routes/collections/[collection_id]/+page.svelte
```

#### Strategy 2: Incremental Feature Building

For iterative improvements, use this approach:

```
PR 1: Add basic component structure (no functionality)
PR 2: Add first functionality (e.g., text search)
PR 3: Add second functionality (e.g., image upload)
PR 4: Add third functionality (e.g., drag and drop)
PR 5: Polish and optimize
```

### What Makes a Good Atomic PR?

#### ✅ Good PR Characteristics

1. **Single Responsibility**
   - Addresses one feature, bug fix, or refactoring
   - Has a clear, focused purpose

2. **Self-Contained**
   - Can be reviewed and tested independently
   - Doesn't break existing functionality
   - All tests pass

3. **Properly Tested**
   - Includes tests for new functionality
   - Updates existing tests if needed
   - Test coverage doesn't decrease

4. **Well-Documented**
   - Clear PR description
   - Updated documentation if needed
   - Code comments for complex logic

#### ❌ Bad PR Characteristics

1. **Too Large**
   - Over 300 lines of changes
   - Multiple unrelated changes
   - Mixes features, refactoring, and bug fixes

2. **Incomplete**
   - Adds code that isn't used anywhere
   - Missing tests
   - Breaks existing functionality

3. **Poorly Organized**
   - Random order of changes
   - Mixes formatting changes with logic changes
   - Hard to understand the progression

### PR Ordering Best Practices

#### Order of Introduction

**Rule: Dependencies before dependents**

Always introduce lower-level code before higher-level code:

```typescript
// ❌ Bad: Component before its dependencies
PR 1: Add GridSearch component (uses useFileUpload)
PR 2: Add useFileUpload hook  // <- GridSearch is already using it!

// ✅ Good: Dependencies first
PR 1: Add useFileUpload hook
PR 2: Add GridSearch component (uses useFileUpload)
```

**Why this matters:**

- Each PR can be merged independently
- No "dead code" or unused functions in intermediate state
- Easier to review - reviewers see the building blocks first
- Natural progression that's easy to follow
- Can be deployed incrementally without breaking production

#### Real Example: Bottom-Up PR Sequence

```
// Building a video player feature

✅ PR 1: Add video utility functions
   - getVideoDuration()
   - formatTimestamp()
   - parseVideoMetadata()
   Purpose: Pure utilities, no dependencies

✅ PR 2: Add useVideoPlayer hook
   - Uses utilities from PR 1
   - Manages video state
   - Provides play/pause/seek methods
   Purpose: Reusable video player logic

✅ PR 3: Add VideoControls component
   - Uses useVideoPlayer hook from PR 2
   - Play/pause button
   - Progress bar
   - Volume control
   Purpose: Basic UI controls

✅ PR 4: Add VideoPlayer component
   - Uses VideoControls from PR 3
   - Uses useVideoPlayer from PR 2
   - Combines video element + controls
   Purpose: Complete video player

✅ PR 5: Integrate VideoPlayer into media gallery
   - Uses VideoPlayer from PR 4
   - Adds to gallery page
   Purpose: Final integration
```

### Splitting Work into Multiple PRs

When you have multiple changes ready but need to split them into separate PRs, use one of these strategies:

#### Strategy 1: Interactive Staging (Recommended for Simple Splits)

Split changes by staging files selectively:

```bash
# You have: hookY, ComponentA, ComponentB all changed

# Create branch for PR 1 (hookY)
git checkout -b feat/add-use-y-hook main
git add src/lib/hooks/useY/
git commit -m "Add useY hook + tests"
git push -u origin feat/add-use-y-hook

# Create branch for PR 2 (ComponentA) - starts from main, cherry-pick needed files
git checkout -b feat/add-component-a main
git checkout feat/add-use-y-hook -- src/lib/hooks/useY/  # Get the hook
git add src/lib/components/ComponentA/
git commit -m "Add ComponentA using useY hook"
git push -u origin feat/add-component-a

# Create branch for PR 3 (ComponentB)
git checkout -b feat/add-component-b main
git checkout feat/add-use-y-hook -- src/lib/hooks/useY/  # Get the hook
git add src/lib/components/ComponentB/
git commit -m "Add ComponentB using useY hook"
git push -u origin feat/add-component-b
```

#### Strategy 2: Interactive Add (Best for Mixed Changes)

Use `git add -p` to stage parts of files:

```bash
# Create first branch
git checkout -b feat/add-use-y-hook main

# Stage only hook-related changes (even within same files)
git add -p  # Interactively choose hunks
git add src/lib/hooks/useY/  # Add entire hook folder

git commit -m "Add useY hook + tests"
git push -u origin feat/add-use-y-hook

# Remaining changes stay uncommitted - create next branch
git checkout -b feat/add-component-a main
git add src/lib/components/ComponentA/
git commit -m "Add ComponentA"
git push -u origin feat/add-component-a
```

#### Strategy 3: Stacked Branches (For Sequential Dependencies)

Create branches that build on each other:

```bash
# PR 1: Hook
git checkout -b feat/pr1-add-use-y-hook main
git add src/lib/hooks/useY/
git commit -m "Add useY hook + tests"
git push -u origin feat/pr1-add-use-y-hook

# PR 2: ComponentA (built on top of PR 1)
git checkout -b feat/pr2-add-component-a feat/pr1-add-use-y-hook
git add src/lib/components/ComponentA/
git commit -m "Add ComponentA using useY"
git push -u origin feat/pr2-add-component-a

# PR 3: ComponentB (built on top of PR 1)
git checkout -b feat/pr3-add-component-b feat/pr1-add-use-y-hook
git add src/lib/components/ComponentB/
git commit -m "Add ComponentB using useY"
git push -u origin feat/pr3-add-component-b

# After PR 1 merges:
git checkout feat/pr2-add-component-a
git rebase main
git push --force-with-lease

git checkout feat/pr3-add-component-b
git rebase main
git push --force-with-lease
```

#### Strategy 4: Git Worktrees (Advanced - Multiple Directories)

Use worktrees to work on multiple PRs simultaneously without switching branches:

```bash
# Main repo in ~/project/

# Create worktree for PR 1
git worktree add ../project-pr1-hook feat/pr1-add-use-y-hook

# Create worktree for PR 2
git worktree add ../project-pr2-component-a feat/pr2-add-component-a

# Now you have:
# ~/project/           (main branch)
# ~/project-pr1-hook/  (PR 1 branch)
# ~/project-pr2-component-a/ (PR 2 branch)

# Work in each directory independently
cd ../project-pr1-hook
git add src/lib/hooks/useY/
git commit -m "Add useY hook"
git push

cd ../project-pr2-component-a
git add src/lib/components/ComponentA/
git commit -m "Add ComponentA"
git push

# Cleanup when done
git worktree remove ../project-pr1-hook
git worktree remove ../project-pr2-component-a
```

#### Choosing the Right Strategy

| Scenario | Best Strategy | Why |
|----------|---------------|-----|
| Files cleanly separated | Interactive Staging | Simple, fast, no conflicts |
| Changes mixed in same files | Interactive Add (`-p`) | Fine-grained control |
| PRs must be reviewed in order | Stacked Branches | Clear dependencies |
| Many PRs, context switching | Git Worktrees | No branch switching needed |

#### Best Practices

- **Plan before coding**: Know you'll need multiple PRs? Create branches upfront
- **Commit frequently**: Small commits are easier to split later
- **Use descriptive branch names**: Include PR number for stacked branches
- **Test each PR independently**: Don't assume dependencies will be merged
- **Keep worktrees clean**: Remove unused worktrees to avoid confusion

### Handling Dependencies Between PRs

When PRs depend on each other:

1. **Create branches sequentially**

   ```bash
   main -> pr-1-utilities
   pr-1-utilities -> pr-2-hooks
   pr-2-hooks -> pr-3-components
   ```

2. **Update base branch after merge**

   ```bash
   # After PR 1 merges to main
   git checkout pr-2-hooks
   git rebase main
   git push --force-with-lease
   ```

3. **Use draft PRs for visibility**
   - Open PR 2 as draft while PR 1 is in review
   - Shows reviewers the bigger picture
   - Prevents duplicate work

### PR Review Checklist

Before submitting a PR, verify:

- [ ] PR is under 300 lines (excluding tests)
- [ ] PR has a single, clear purpose
- [ ] All new code has tests
- [ ] All tests pass locally
- [ ] Static checks pass (linting, type checking)
- [ ] PR description clearly explains what and why
- [ ] Dependencies are already merged (or in earlier PRs)
- [ ] No unrelated formatting or refactoring changes
- [ ] Documentation is updated if needed
- [ ] Follows the bottom-up approach for new features

### Common Pitfalls

#### ❌ Pitfall 1: "Kitchen Sink" PRs

```
Bad: Single PR with 800 lines
- Adds new component
- Refactors 3 existing components
- Fixes 2 unrelated bugs
- Updates documentation
- Changes formatting in 10 files
```

**Solution:** Split into 5 separate PRs, each focused on one thing.

#### ❌ Pitfall 2: Top-Down Implementation

```
Bad Order:
PR 1: Add page that uses new component (component doesn't exist yet!)
PR 2: Add the component (uses hook that doesn't exist yet!)
PR 3: Add the hook

Result: PRs can't be merged independently
```

**Solution:** Reverse the order - hook → component → page integration.

#### ❌ Pitfall 3: Mixing Refactoring with Features

```
Bad: Single PR
- Adds new feature (300 lines)
- Refactors old code (200 lines)
- Total: 500 lines, hard to review
```

**Solution:** Two PRs - one for refactoring, one for the feature.

### Measuring PR Quality

Good metrics for atomic PRs:

- **Time to review:** Should be < 30 minutes
- **Number of review rounds:** Should be 1-2
- **Lines changed:** Should be < 300
- **Files changed:** Should be < 10
- **Merge conflicts:** Should be rare
- **Time to merge:** Should be < 2 days

