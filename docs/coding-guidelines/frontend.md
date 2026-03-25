# Frontend coding guidelines

This document outlines coding standards and best practices for frontend development in LightlyStudio using SvelteKit and TypeScript.

## Key Principles

- Write concise, technical TypeScript code with minimal dependency on framework-specific features. While Svelte provides powerful features like runes, use them only when necessary within components that are processed by the Svelte compiler.
- Keep your code simple, lean, and readable. Avoid creating components longer than 100 lines. Focus on wise separation of concerns and split code into logical parts. This approach makes the code easier to maintain, understand, and test.
- Embrace Test-Driven Development (TDD) and write tests for your code. Use the [vitest](https://vitest.dev/) testing framework for unit and integration tests. If you need help with testing, ask for assistance or refer to online resources.
- Follow [Svelte's](https://svelte.dev/docs) and [SvelteKit's](https://kit.svelte.dev/docs) official documentation.

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

## Framework-agnostic approach

We follow a framework-agnostic approach, which means we minimize the use of framework-specific structures and logic. This is based on the following engineering principles:

- Clear dependencies and documentation: Framework-specific features like runes are processed without explicit imports, making dependencies less clear. In contrast, using [writable](https://svelte.dev/docs/svelte/svelte-store) always has clear import dependencies and better documentation.
- Reduced framework coupling: The less framework-specific syntax we use, the better it is for code maintainability and understanding.
- Better developer experience: Code that relies less on framework-specific features is easier to understand for developers who might not be deeply familiar with Svelte's internals.
- Future-proofing: Reduced dependency on framework-specific features makes the codebase more resilient to framework updates and changes.
- State management: Prefer using Svelte stores (writable, readable, derived) over runes for state management. Stores provide clear dependencies, better documentation, and are more framework-agnostic. Use runes only when their specific features are necessary for component-level reactivity.

## Naming Conventions

- Use PascalCase for component names (e.g., `components/AuthForm.svelte`).
- Use camelCase for non-component files (e.g., `hooks/useAuth.ts`).
- Use camelCase for variables, functions, and props (e.g., `const myVariable = 0;`).
- Use the component or function name as a prefix for related logic files (e.g., tests).

```
src/
  components/
    MyComponent/
      MyComponent.svelte
      MyComponent.test.ts
```

## Import/Export Conventions

- Use absolute imports for components and hooks. Example:

```typescript
import { useData } from "$lib/hooks/useData";
```

instead of:

```typescript
import { useData } from "../../../lib/hooks/useData";
```

- Use relative imports only for local files. Example:

```typescript
import { useData } from "./useData";
```

## TypeScript Usage

- Use TypeScript for all code
- Use interfaces for props.
  E.g.:

```typescript
interface UseDataProps {
    title: string;
    onClick: () => void;
}

interface UseDataReturn {
    title: string;
    onClick: () => void;
}

export function useData(props: UseDataProps): UseDataReturn {
    ...
}
```

- Avoid exporting/importing types. Instead, use [TypeScript utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html) to derive types from existing code. This approach:
  - Reduces type duplication
  - Ensures type consistency with the source code
  - Makes refactoring easier as types automatically update with code changes
  - Keeps the codebase DRY (Don't Repeat Yourself)

Common utility type patterns:

```typescript
// Derive parameter types from a function
type UseDataParams = Parameters<typeof useData>;

// Derive return type from a function
type UseDataReturn = ReturnType<typeof useData>;

// Make all properties optional
type PartialData = Partial<UseDataProps>;

// Pick specific properties
type TitleOnly = Pick<UseDataProps, "title">;

// Omit specific properties
type WithoutTitle = Omit<UseDataProps, "title">;

// Make all properties required
type RequiredData = Required<Partial<UseDataProps>>;

// Create a type from an object's keys
type DataKeys = keyof UseDataProps;
```

## UI and Styling

- Use [Shadcn](https://next.shadcn-svelte.com/) components for pre-built, customizable UI elements. Shadcn is a collection of re-usable components built using [Bits-UI](https://www.bits-ui.com/) and [Tailwind CSS](https://tailwindcss.com/). It's not a component library but rather a collection of re-usable components that you can copy and customize for your project.
- Use [Bits-UI](https://www.bits-ui.com/) as the base component library. Bits-UI is a collection of unstyled, accessible components for Svelte. It provides the foundation for our Shadcn components.

### Component Import Guidelines

#### Using Shadcn Components (`$lib/components/ui`)

- Import and use Shadcn components directly from `$lib/components/ui` for basic UI elements that don't require project-specific customization. These components are pre-styled and follow our design system.
- Examples of when to use Shadcn components directly:
  - Basic form elements (inputs, buttons, checkboxes)
  - Layout components (cards, containers)
  - Navigation elements (tabs, dropdowns)
  - Feedback components (alerts, toasts)
  - Data display components (tables, lists)

```typescript
// Good: Using Shadcn components directly for basic UI elements
import { Button } from '$lib/components/ui/button';
import { Input } from '$lib/components/ui/input';

<Button>Submit</Button>
<Input placeholder="Enter text" />
```

#### Using LightlyStudio Components (`$lib/components`)

- Import from `$lib/components` for project-specific components that:
  - Combine multiple Shadcn components
  - Add project-specific business logic
  - Implement complex interactions
  - Require custom styling beyond Shadcn's defaults
  - Need to maintain consistent behavior across the application

```typescript
// Good: Using project-specific components for complex features
import { DatasetCard } from '$lib/components';
import { AnnotationToolbar } from '$lib/components';

<DatasetCard dataset={dataset} />
<AnnotationToolbar onSave={handleSave} />
```

#### Component Composition

- When building new components, prefer composition over inheritance
- Use Shadcn components as building blocks for more complex components
- Keep component logic separate from UI elements

```typescript
// Good: Composing components
<script lang="ts">
  import { Card } from '$lib/components/ui/card';
  import { Button } from '$lib/components/ui/button';
  import { useDataset } from '$lib/hooks/useDataset';

  const { dataset, isLoading } = useDataset();
</script>

<Card>
  {#if isLoading}
    <LoadingSpinner />
  {:else}
    <h2>{dataset.name}</h2>
    <Button>View Details</Button>
  {/if}
</Card>
```

#### Explicit Props vs. Prop Spreading

- Prefer explicit props over blindly spreading objects into components
- Components should only receive the specific props they need, making the interface clear and maintainable
- Avoid spreading entire objects unless the component is intentionally designed as a proxy/wrapper

**Benefits of explicit props:**

- **Type safety**: Clear understanding of what props the component uses
- **Maintainability**: Easy to track which props are relevant
- **Intent clarity**: The relationship between data and UI is explicit
- **Refactoring safety**: Changes to object shapes won't silently break components

```typescript
// Bad: Blind object spreading - unclear what props are actually used
<script lang="ts">
  interface User {
    id: string;
    name: string;
    email: string;
    age: number;
    address: string;
    // ... many other fields
  }

  const user: User = getUserData();
</script>

<UserCard {...user} />

// Good: Explicit props - clear interface and intent
<script lang="ts">
  interface User {
    id: string;
    name: string;
    email: string;
    age: number;
    address: string;
    // ... many other fields
  }

  const user: User = getUserData();
</script>

<UserCard name={user.name} email={user.email} />
```

**Exception**: Spreading is acceptable when:

- Forwarding HTML attributes using `...rest` pattern
- The component is intentionally designed as a wrapper/proxy
- You immediately destructure with explicit TypeScript types in the component definition

- Organize Tailwind classes using the `cn()` utility from `$lib/utils`. This utility helps combine Tailwind classes conditionally and prevents class conflicts.

### Icons

- Use [Lucide Icons](https://lucide.dev/icons/) for all icons in the application.
- Import icons directly from `@lucide/svelte`:

```typescript
import { Check, X, ChevronDown } from "@lucide/svelte";
```

- Use descriptive icon names that match their purpose in the UI.
- Keep icon imports at the top of the script section with other imports.

## Component Development

- Create .svelte files for Svelte components in `src/components`.
- Create directory for each component with the following structure to scope it:

```
src/
  components/
    MyComponent/
      MyComponent.svelte
      MyComponent.helpers.ts
      MyComponent.test.ts
```

- Use subcomponents for complex components:

```
src/
  components/
    MyComponent/
      MyComponent.svelte
      MyComponent.test.ts
      SubComponentA/
        SubComponentA.svelte
        SubComponentA.test.ts
      SubComponentB/
        SubComponentB.svelte
        SubComponentB.test.ts
```

- Use .svelte.ts files for component logic and state machines.
- Implement proper component composition and reusability.
- Use Svelte's props for data passing.
- Leverage Svelte's reactive declarations for local state management.
- Leverage [$app/state](https://svelte.dev/tutorial/kit/page-state) for global state management and access to already loaded data.

## Component Optimization Principles

### SOLID Principles for Components

Apply SOLID principles to create maintainable, scalable components:

#### 1. Single Responsibility Principle (SRP)

Each component should have one clear purpose and one reason to change.

**Bad Example** - Component doing too much:

```typescript
// ❌ UserDashboard.svelte - handles authentication, data fetching, rendering, and navigation
<script lang="ts">
    import { writable } from 'svelte/store';

    const user = writable(null);
    const isAuthenticated = writable(false);
    const userPosts = writable([]);
    const notifications = writable([]);

    async function login() { /* auth logic */ }
    async function fetchUserData() { /* fetch logic */ }
    async function fetchPosts() { /* posts logic */ }
    async function navigateToProfile() { /* navigation */ }
</script>

<!-- Complex UI mixing concerns -->
```

**Good Example** - Separated responsibilities:

```typescript
// ✅ UserDashboard.svelte - only orchestrates child components
<script lang="ts">
    import { useAuth } from '$lib/hooks/useAuth';
    import { useUserData } from '$lib/hooks/useUserData';
    import UserProfile from './UserProfile/UserProfile.svelte';
    import UserPosts from './UserPosts/UserPosts.svelte';
    import NotificationPanel from './NotificationPanel/NotificationPanel.svelte';

    const { isAuthenticated } = useAuth();
    const { user } = useUserData();
</script>

{#if $isAuthenticated}
    <UserProfile {user} />
    <UserPosts userId={user.id} />
    <NotificationPanel userId={user.id} />
{/if}
```

#### 2. Open/Closed Principle (OCP)

Components should be open for extension but closed for modification. Use composition and configuration over changing existing code.

**Bad Example** - Hardcoded variations:

```typescript
// ❌ Button.svelte - needs modification for each new variant
<script lang="ts">
    export let type: 'primary' | 'secondary' | 'danger' | 'success';
</script>

<button class={type === 'primary' ? 'bg-blue-500' :
               type === 'secondary' ? 'bg-gray-500' :
               type === 'danger' ? 'bg-red-500' : 'bg-green-500'}>
    <slot />
</button>
```

**Good Example** - Extensible through composition:

```typescript
// ✅ Button.svelte - accepts custom classes
<script lang="ts">
    import { cn } from '$lib/utils';

    export let variant: 'primary' | 'secondary' | 'danger' = 'primary';
    export let class: string = '';

    const variantClasses = {
        primary: 'bg-blue-500',
        secondary: 'bg-gray-500',
        danger: 'bg-red-500'
    };
</script>

<button class={cn(variantClasses[variant], class)}>
    <slot />
</button>
```

#### 3. Liskov Substitution Principle (LSP)

Child components should be substitutable for their parent components without breaking functionality.

**Good Example** - Consistent interface:

```typescript
// ✅ Both components accept the same props interface and can be used interchangeably

// TextSearchInput.svelte
<script lang="ts">
    export let value: string;
    export let onSearch: (query: string) => void;
    export let placeholder: string = 'Search by text';
</script>

// ImageSearchInput.svelte
<script lang="ts">
    export let value: string;
    export let onSearch: (query: string) => void;
    export let placeholder: string = 'Search by image';
</script>
```

#### 4. Interface Segregation Principle (ISP)

Don't force components to depend on props they don't use. Keep interfaces minimal and specific.

**Bad Example** - Bloated props:

```typescript
// ❌ UserCard.svelte - receives entire user object but only uses 2 fields
<script lang="ts">
    export let user: {
        id: string;
        name: string;
        email: string;
        age: number;
        address: string;
        phoneNumber: string;
        // ... 20 more fields
    };
</script>

<div>
    <h3>{user.name}</h3>
    <p>{user.email}</p>
</div>
```

**Good Example** - Minimal props:

```typescript
// ✅ UserCard.svelte - only receives what it needs
<script lang="ts">
    export let name: string;
    export let email: string;
</script>

<div>
    <h3>{name}</h3>
    <p>{email}</p>
</div>
```

#### 5. Dependency Inversion Principle (DIP)

Depend on abstractions (hooks, stores) rather than concrete implementations.

**Bad Example** - Direct API calls in component:

```typescript
// ❌ UserList.svelte - tightly coupled to API
<script lang="ts">
    import { writable } from 'svelte/store';

    const users = writable([]);

    async function loadUsers() {
        const response = await fetch('/api/users');
        users.set(await response.json());
    }
</script>
```

**Good Example** - Depend on abstraction:

```typescript
// ✅ UserList.svelte - depends on hook abstraction
<script lang="ts">
    import { useUsers } from '$lib/hooks/useUsers';

    const { data: users, isLoading } = useUsers();
</script>

{#if $isLoading}
    <p>Loading...</p>
{:else}
    {#each $users as user}
        <UserCard name={user.name} email={user.email} />
    {/each}
{/if}
```

### Reducing Complexity

#### 1. Horizontal Complexity (Width)

Reduce the number of things a component does at once.

**Metrics:**

- Number of props (keep < 7)
- Number of state variables (keep < 5)
- Number of event handlers (keep < 5)
- Number of imports (keep < 10)

**Example - Reducing horizontal complexity:**

```typescript
// ❌ Before: Too many responsibilities (6 state variables, 7 event handlers, 5 imports)
<script lang="ts">
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
    import { useFileUpload } from '$lib/hooks/useFileUpload/useFileUpload';
    import { writable } from 'svelte/store';

    const activeImage = writable<string | null>(null);
    const submittedQueryText = writable('');
    const previewUrl = writable<string | null>(null);
    const query_text = writable('');
    const fileInput = writable<HTMLInputElement | null>(null);
    const dragOver = writable(false);

    function handleDragOver() { /* ... */ }
    function handleDragLeave() { /* ... */ }
    function handleDrop() { /* ... */ }
    function handlePaste() { /* ... */ }
    function handleFileSelect() { /* ... */ }
    function onKeyDown() { /* ... */ }
    function clearSearch() { /* ... */ }
</script>
```

**✅ After: Split into smaller components and hooks**

```typescript
// GridSearch.svelte - orchestrator only
<script lang="ts">
    import { useImageUploadHandlers } from './hooks/useImageUploadHandlers';
    import SearchInput from './SearchInput/SearchInput.svelte';
    import ActiveSearchDisplay from './ActiveSearchDisplay/ActiveSearchDisplay.svelte';

    const { dragOver, handleDragOver, handleDrop } = useImageUploadHandlers();
    // Much simpler!
</script>

// SearchInput.svelte - handles text input
// ActiveSearchDisplay.svelte - handles display
// useImageUploadHandlers.ts - handles file upload logic
```

#### 2. Vertical Complexity (Depth)

Reduce nesting and deeply nested logic.

**Metrics:**

- Nesting depth (keep < 3 levels)
- Lines of code in component (keep < 150 lines)
- Lines in functions (keep < 20 lines)

**Example - Reducing vertical complexity:**

```typescript
// ❌ Before: Deep nesting (4 levels)
function processUser(user) {
  if (user) {
    if (user.isActive) {
      if (user.permissions) {
        if (user.permissions.includes("admin")) {
          return "Admin User";
        }
      }
    }
  }
  return "Regular User";
}

// ✅ After: Early returns (1-2 levels)
function processUser(user) {
  if (!user) return "Regular User";
  if (!user.isActive) return "Regular User";
  if (!user.permissions) return "Regular User";
  if (!user.permissions.includes("admin")) return "Regular User";

  return "Admin User";
}
```

#### 3. Cyclomatic Complexity

Reduce the number of independent paths through code.

**Metrics:**

- Number of conditional branches (keep < 5 per function)
- Number of logical operators (&&, ||) per expression (keep < 3)

**Example - Reducing cyclomatic complexity:**

```typescript
// ❌ Before: High cyclomatic complexity (CC = 8)
function validateUser(user: User) {
  if (user.name && user.email) {
    if (user.age > 18 || user.hasParentalConsent) {
      if (user.country === "US" || user.country === "CA") {
        if (user.verified && !user.banned) {
          return true;
        }
      }
    }
  }
  return false;
}

// ✅ After: Reduced complexity (CC = 4)
function validateUser(user: User) {
  const hasBasicInfo = user.name && user.email;
  const isAgeCompliant = user.age > 18 || user.hasParentalConsent;
  const isAllowedCountry = ["US", "CA"].includes(user.country);
  const hasGoodStanding = user.verified && !user.banned;

  return hasBasicInfo && isAgeCompliant && isAllowedCountry && hasGoodStanding;
}
```

### Component Splitting Guidelines

#### When to Split Components

Split a component when:

1. **It exceeds 100 lines** (including markup and script)
2. **It has multiple distinct UI sections** that could be named separately
3. **Logic and presentation are mixed** - extract logic to hooks
4. **You find yourself scrolling** to understand the component
5. **Testing becomes difficult** due to many responsibilities

#### How to Split Components

**Strategy 1: Extract Subcomponents**

```typescript
// ❌ Before: Monolithic component (200+ lines)
// GridSearch.svelte
<script>
    // 100 lines of logic
</script>

<div>
    <!-- Search input UI -->
    <!-- Active search display UI -->
    <!-- Upload handling UI -->
</div>

// ✅ After: Split into focused subcomponents
// GridSearch.svelte (50 lines)
<script>
    import SearchInput from './SearchInput/SearchInput.svelte';
    import ActiveSearchDisplay from './ActiveSearchDisplay/ActiveSearchDisplay.svelte';
</script>

<div>
    {#if hasActiveSearch}
        <ActiveSearchDisplay />
    {:else}
        <SearchInput />
    {/if}
</div>

// SearchInput/SearchInput.svelte (40 lines)
// ActiveSearchDisplay/ActiveSearchDisplay.svelte (50 lines)
```

**Strategy 2: Extract Hooks**

```typescript
// ❌ Before: Logic mixed with UI (100+ lines in component)
<script lang="ts">
    import { writable } from 'svelte/store';

    const dragOver = writable(false);

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        dragOver.set(true);
    }

    function handleDrop(e: DragEvent) {
        e.preventDefault();
        const files = Array.from(e.dataTransfer?.files || []);
        // 30 more lines of file handling...
    }
</script>

// ✅ After: Extract to hook (component now 40 lines, hook 50 lines)
<script lang="ts">
    import { useImageUpload } from './hooks/useImageUpload';

    const { dragOver, handleDragOver, handleDrop } = useImageUpload();
</script>

// hooks/useImageUpload.ts - 50 lines of pure, testable logic
```

**Strategy 3: Extract Configuration**

```typescript
// ❌ Before: Hardcoded configuration mixed with logic
const MAX_SIZE = 50 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg"];

// ✅ After: Extract to constants file
// constants/upload.ts
export const UPLOAD_CONFIG = {
  MAX_SIZE: 50 * 1024 * 1024,
  ALLOWED_TYPES: ["image/png", "image/jpeg"],
} as const;
```

### Real Example: GridSearch Component Optimization

**Before optimization** (GridSearch.svelte - 131 lines, multiple responsibilities):

- Text search handling
- Image upload handling
- Drag and drop logic
- File input management
- State management
- API integration
- Error handling

**After optimization:**

- **GridSearch.svelte** (50 lines) - Orchestration only
- **SearchInput.svelte** (40 lines) - Text input UI
- **ActiveSearchDisplay.svelte** (50 lines) - Search results display
- **useImageUploadHandlers.ts** (60 lines) - File upload logic
- **useFileUpload.ts** (80 lines) - Generic file upload hook

**Benefits:**

- **Each file has one clear purpose** (SRP)
- **Reduced horizontal complexity** (fewer props, state variables)
- **Reduced vertical complexity** (no deep nesting)
- **Lower cyclomatic complexity** (simpler conditionals)
- **Better testability** (each piece can be tested in isolation)
- **Better reusability** (useFileUpload can be used elsewhere)

### Complexity Checklist

Before finishing a component, check:

- [ ] Component is under 100 lines
- [ ] Function is under 20 lines
- [ ] Nesting depth is under 3 levels
- [ ] Props count is under 7
- [ ] State variables count is under 5
- [ ] Event handlers count is under 5
- [ ] Cyclomatic complexity is under 5 per function
- [ ] Component has one clear responsibility
- [ ] Logic is separated from presentation
- [ ] No hardcoded configuration mixed with logic
- [ ] Easy to test in isolation

### Page State Access

Use `$app/state` instead of `$app/stores` for accessing page state.

**Bad Example:**

```typescript
import { page } from "$app/stores";

// Accessing params with stores requires $ prefix
$page.params.sampleId;
```

**Good Example:**

```typescript
import { page } from "$app/state";

// Accessing params directly without $ prefix
page.params.sampleId;
```

## State Management

- use reusable tiny hooks to avoid one big store for all the state management. E.g. [useTags](../../lightly_studio_view/src/lib/hooks/useTags/useTags.ts).
- Separate state management logic from the component logic as much as possible for better maintanance. Use `src/lib/hooks` for reusable hooks.

### Svelte 5 Syntax

#### Event Handlers

Use Svelte 5 event handler syntax (`onclick`, `onchange`, etc.) instead of Svelte 4 syntax (`on:click`, `on:change`).

**Bad Example (Svelte 4):**

```typescript
<button on:click={() => handleClick()}>Click me</button>
<input on:change={(e) => handleChange(e)} />
```

**Good Example (Svelte 5):**

```typescript
<button onclick={() => handleClick()}>Click me</button>
<input onchange={(e) => handleChange(e)} />
```

#### Reactive Declarations

Avoid using Svelte 4 reactive syntax (`$:`) in new code. Instead, use Svelte 5 runes or derived stores.

**Bad Example (Svelte 4):**

```typescript
$: fullName = firstName + " " + lastName;
$: isValid = email.includes("@");
```

**Good Example (Svelte 5 Runes):**

```typescript
const fullName = $derived(firstName + " " + lastName);
const isValid = $derived(email.includes("@"));
```

**Good Example (Svelte Stores - Framework-agnostic):**

```typescript
import { derived } from "svelte/store";

const fullName = derived([firstName, lastName], ([$firstName, $lastName]) => {
  return $firstName + " " + $lastName;
});
```

### Avoid Mixing Svelte 4 Stores with Svelte 5 Runes

Do not mix `derived` from `svelte/store` with `$derived` rune syntax. Choose one approach and use it consistently.

**Bad Example:**

```typescript
import { derived } from "svelte/store";
import { annotationFilterLabels } from "./stores";

// ❌ Wrong: Trying to use $derived on the derived function
const selectedAnnotationFilter = $derived.by(() => {
  const labelsMap = $annotationFilterLabels;
  // ... logic
});
```

**Good Example (Svelte 5 Runes):**

```typescript
import { annotationFilterLabels } from "./stores";

// ✅ Correct: Using $derived.by() without importing derived
const selectedAnnotationFilter = $derived.by(() => {
  const labelsMap = $annotationFilterLabels;
  // ... logic
});
```

**Good Example (Svelte 4 Stores):**

```typescript
import { derived } from "svelte/store";
import { annotationFilterLabels } from "./stores";

// ✅ Correct: Using derived() to create a store
const selectedAnnotationFilter = derived(
  annotationFilterLabels,
  ($annotationFilterLabels) => {
    // ... logic
    return result;
  },
);

// Then use it with $selectedAnnotationFilter in components
```

E.g. [separate state management example](https://svelte.dev/playground/hello-world?version=5.32.1#H4sIAAAAAAAAE3WRwW6DMBBEf2W1qhSioqS9koBU9TNKD8TZVFZhjex1kwr53yvjhkCVXjisZ2aHtwNy0xEW6B29Gs9CFujSdH1LmONJt-SweBtQvvuoigPMr56Xvt-4L2olzg6No3tzZViIxWGBe6es7gXahj_KGsXVWNUMAKC73liBAWY1Apys6WC12d6GG3GrXc3JpAy76FHxLQfNylJHLBCgnAVl613N-23aXUXz_uBFDINh1Wr1WQ7ZGsrqFpCtw2-vMaKA4WHcEWJO8lY1Y45CF8FCrKeQ_8No0X2J6e_TjNTE42y1NIeWJhqJ69aJsZRQJAxjQSgnw559dyBbZU_rUUWXMfHkWYk2vOADQ_rb9J0kMx5XRcLuWTa-PzZCWaZGdAoe4TkuioJwPdCUZMmRjOvuRTmS1HJhtiTe8p3z5rM4CLuaw_IS7zlKo9uz5iMWp6Z1FH4Aaa7hNOYCAAA=):

```typescript
// File: useCounter.ts
import { writable } from 'svelte/store';

const count = writable<number>(0);

export function useCounter() {

    function increment() {
        count.update((c) => c + 1);
    }

    function resetCount() {
        count.set(0);
    }

    return { count, increment, resetCount };
}

// File: Counter.svelte
<script lang="ts">
    import { useCounter } from './useCounter.ts';

    const { count, increment } = useCounter();
</script>

<button onclick={() => increment()}>
    Count: {$count}
</button>
```

## Routing and Pages

- Utilize [SvelteKit's file-based routing system in the src/routes/](https://svelte.dev/tutorial/kit/layouts) directory.
- Utilize dynamic routes using [slug](https://svelte.dev/tutorial/kit/params) syntax. E.g. sample details [example](../../lightly_studio_view/src/routes/samples/[sample_id]/).
- Use +layout.svelte for shared layout components. E.g. [shared layout for samples/annotations Grid](../../lightly_studio_view/src/routes/collections/[collection_id]/+layout.svelte).

## Data Fetching and API Routes

- We leverage the [hook design pattern](https://medium.com/@beecodeguy/the-hook-pattern-building-reusable-logic-db6db49b83be) to write scalable and maintainable code. E.g. [useFeatureFlags](../../lightly_studio_view/src/lib/hooks/useFeatureFlags/useFeatureFlags.ts). You can use this pattern to create reusable hooks for data fetching, state management, and other logic.
- We don't use `services` folder for data fetching. Instead, we use hooks. Unless we have a specific reason to create a service, we use a hook design pattern.
- Implement proper error handling for data fetching operations.
- Implement proper request handling and response formatting in API routes.

## Hook design pattern

- Use the hook design pattern for reusable logic and state management.
- Put it to `src/lib/hooks` if it is a generic hook that can be reused in multiple components. Put it to the component directory if it is a specific hook that is only used in that component.

```typescript
// hooks/useUsers.ts
export function useUsers() {
  const isLoading = writable(false);
  const users = writable<User[]>([]);
  const error = writable<Error | null>(null);

  async function fetchUsers() {
    isLoading.set(true);
    try {
      const response = await fetch("/api/users");
      const data = await response.json();
      users.set(data);
    } catch (err) {
      error.set(err instanceof Error ? err : new Error(String(err)));
    } finally {
      isLoading.set(false);
    }
  }

  return { data: users, isLoading, error, fetchUsers };
}
```

## Storybook

### Story Syntax

When creating Storybook stories, use the simplified syntax without explicit `{#snippet children()}` blocks for better readability:

**Good Example:**

```typescript
<Story name="H1" args={{ variant: 'h1' }}>
    Heading 1 - Large Page Title
</Story>
```

**Bad Example:**

```typescript
<Story name="H1" args={{ variant: 'h1' }}>
    {#snippet children()}
        Heading 1 - Large Page Title
    {/snippet}
</Story>
```

The explicit snippet syntax is not required for simple text content and makes stories less readable.

## Testing

### Motivation

- Writing the tests is a crucial part of the development process.
- It helps to ensure that your code works as expected and prevents regressions in the future.
- It shows maturity of the code and helps to write the more scalable and maintainable code.
- It helps you to understand the requirements better.

### Testing levels

- Unit tests: Test individual components and functions in isolation.
- Integration tests: Test the interaction between components and functions.
- End-to-end tests: Test the entire application flow, including routing and API interactions.

##### Unit tests

To test individual components and functions in isolation.

```typescript
import { render, screen } from "@testing-library/svelte";
import MyComponent from "./MyComponent.svelte";

describe("MyComponent", () => {
  it("renders the title", () => {
    render(MyComponent, { props: { title: "Hello World" } });
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });
});
```

##### Integration tests

To test the interaction between components and functions. It tests the integration of multiple components and their interactions with each other.

```typescript
import { render, screen } from "@testing-library/svelte";
import MyComponent from "./MyComponent.svelte";
import { fireEvent } from "@testing-library/svelte";
import { useCounter } from "./useCounter.ts";

describe("MyComponent calls useCounter", () => {
  it("calls the increment function when clicked", async () => {
    const { increment } = useCounter();
    const incrementSpy = jest.spyOn(increment, "increment");
    render(MyComponent);
    await fireEvent.click(screen.getByRole("button"));
    expect(incrementSpy).toHaveBeenCalled();
  });
});
```

### Test Optimization Principles

When writing tests, focus on quality over quantity. Follow these principles to minimize duplication and keep tests maintainable:

#### 1. Use Helper Functions for Repeated Setup

Create `defaultProps` or setup functions to eliminate repeated prop objects:

```typescript
// Good: DRY approach with defaultProps
describe("SearchInput", () => {
  const defaultProps = {
    queryText: "",
    isUploading: false,
    onkeydown: vi.fn(),
    onpaste: vi.fn(),
  };

  it("renders with correct placeholder", () => {
    render(SearchInput, { props: defaultProps });
    expect(screen.getByPlaceholderText("Search")).toBeInTheDocument();
  });

  it("disables input when uploading", () => {
    render(SearchInput, { props: { ...defaultProps, isUploading: true } });
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});

// Bad: Repeated prop objects
describe("SearchInput", () => {
  it("renders with correct placeholder", () => {
    render(SearchInput, {
      props: {
        queryText: "",
        isUploading: false,
        onkeydown: vi.fn(),
        onpaste: vi.fn(),
      },
    });
    expect(screen.getByPlaceholderText("Search")).toBeInTheDocument();
  });

  it("disables input when uploading", () => {
    render(SearchInput, {
      props: {
        queryText: "",
        isUploading: true,
        onkeydown: vi.fn(),
        onpaste: vi.fn(),
      },
    });
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
```

#### 2. Avoid Testing Opposites

Don't test both enabled and disabled states - testing one implies the other:

```typescript
// Good: Test only one state
it("disables input when isUploading is true", () => {
  render(SearchInput, { props: { ...defaultProps, isUploading: true } });
  expect(screen.getByRole("textbox")).toBeDisabled();
});

// Bad: Testing the opposite is redundant
it("enables input when isUploading is false", () => {
  render(SearchInput, { props: defaultProps });
  expect(screen.getByRole("textbox")).not.toBeDisabled();
});
```

#### 3. Combine Related Tests

Merge tests that check related functionality:

```typescript
// Good: Combined test
it("renders both search and image icons", () => {
  const { container } = render(SearchInput, { props: defaultProps });
  expect(container.querySelectorAll("svg").length).toBe(2);
});

// Bad: Separate tests for the same concept
it("renders search icon", () => {
  const { container } = render(SearchInput, { props: defaultProps });
  expect(container.querySelectorAll("svg").length).toBeGreaterThan(0);
});

it("renders image icon", () => {
  const { container } = render(SearchInput, { props: defaultProps });
  expect(container.querySelectorAll("svg").length).toBe(2);
});
```

#### 4. Avoid Testing Implementation Details

Don't test internal implementation details like CSS classes or internal structure:

```typescript
// Bad: Testing CSS classes (implementation detail)
it("renders with correct CSS classes for layout", () => {
  const { container } = render(ActiveSearchDisplay, { props: defaultProps });
  const wrapper = container.querySelector(
    ".flex.h-10.w-full.items-center.rounded-md.border.border-input.bg-background",
  );
  expect(wrapper).toBeInTheDocument();
});

// Good: Test user-visible behavior instead
it("displays active search query", () => {
  render(ActiveSearchDisplay, {
    props: { ...defaultProps, submittedQueryText: "test" },
  });
  expect(screen.getByText("test")).toBeInTheDocument();
});
```

#### 5. Test Behavior, Not Configuration

Focus on component behavior rather than testing how hooks are configured:

```typescript
// Bad: Testing hook configuration (implementation detail)
it("calls useEmbedText with correct parameters", () => {
  render(GridSearch);
  expect(mockUseEmbedText).toHaveBeenCalledWith({
    collectionId: "test-collection-id",
    queryText: "",
    embeddingModelId: null,
  });
});

// Good: Test the actual behavior
it("displays search results when query is submitted", async () => {
  render(GridSearch);
  await userEvent.type(screen.getByRole("textbox"), "test query");
  await userEvent.keyboard("{Enter}");
  expect(screen.getByText("test query")).toBeInTheDocument();
});
```

#### 6. Remove Duplicate Tests

Identify and remove tests that verify the same behavior:

```typescript
// Bad: Both tests check the same thing
it("renders SearchInput when no active search", () => {
  render(GridSearch);
  const input = screen.getByPlaceholderText("Search samples");
  expect(input).toBeInTheDocument();
});

it("shows SearchInput initially", () => {
  render(GridSearch);
  expect(screen.getByTestId("search-input")).toBeInTheDocument();
});

// Good: One test is sufficient
it("shows SearchInput initially", () => {
  render(GridSearch);
  expect(screen.getByTestId("search-input")).toBeInTheDocument();
});
```

#### Example: Optimizing Test Suite

**Before optimization** (51 tests with duplication):

- Repeated prop objects in every test
- Tests for both enabled and disabled states
- Separate tests for related functionality
- Tests for CSS classes and internal structure
- Tests for hook configuration
- Duplicate tests for the same behavior

**After optimization** (46 tests, cleaner and more maintainable):

- `defaultProps` helper eliminates duplication
- Only test one state (disabled/enabled)
- Combined related tests (icon rendering)
- Removed CSS class tests
- Removed hook configuration tests
- Removed duplicate tests

This approach results in:

- **~10% fewer tests** while maintaining full coverage
- **Better test maintainability** with less duplication
- **Faster test execution** with fewer redundant tests
- **Clearer test intent** by focusing on behavior

### Running Tests and Checks

Before submitting code, always run the following commands to ensure code quality:

```bash
# Run static checks (type checking, linting, formatting)
make static-checks

# Run tests
npm run test:unit
```

The `make static-checks` command will:

- Run TypeScript type checking
- Run ESLint for code quality
- Run Prettier to verify formatting
- Run Svelte check for component validation

Make sure all checks pass before committing your changes.
