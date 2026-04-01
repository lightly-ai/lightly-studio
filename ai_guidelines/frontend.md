# Frontend coding guidelines

This document outlines coding standards and best practices for frontend development in LightlyStudio using SvelteKit and TypeScript.

## Key Principles

- Write concise, technical TypeScript code with minimal dependency on framework-specific features. While Svelte provides powerful features like runes, use them only when necessary within components that are processed by the Svelte compiler.
- Keep your code simple, lean, and readable. Avoid creating components longer than 100 lines. Focus on wise separation of concerns and split code into logical parts. This approach makes the code easier to maintain, understand, and test.
- Embrace Test-Driven Development (TDD) and write tests for your code. Use the [vitest](https://vitest.dev/) testing framework for unit and integration tests. If you need help with testing, ask for assistance or refer to online resources.
- Follow [Svelte's](https://svelte.dev/docs) and [SvelteKit's](https://kit.svelte.dev/docs) official documentation.

## Framework-agnostic approach

We follow a framework-agnostic approach, which means we minimize the use of framework-specific structures and logic. This is based on the following engineering principles:

- Clear dependencies and documentation: Framework-specific features like runes are processed without explicit imports, making dependencies less clear. In contrast, using [writable](https://svelte.dev/docs/svelte/svelte-store) always has clear import dependencies and better documentation.
- Reduced framework coupling: The less framework-specific syntax we use, the better it is for code maintainability and understanding.
- Better developer experience: Code that relies less on framework-specific features is easier to understand for developers who might not be deeply familiar with Svelte's internals.
- Future-proofing: Reduced dependency on framework-specific features makes the codebase more resilient to framework updates and changes.
- State management: Prefer using Svelte stores (writable, readable, derived) over runes for state management. Stores provide clear dependencies, better documentation, and are more framework-agnostic. Use runes only when their specific features are necessary for component-level reactivity.

## Naming Conventions

- Use PascalCase for component names and their folders (e.g., `components/AuthForm/AuthForm.svelte`).
- Use camelCase for non-component files (e.g., `hooks/useAuth/useAuth.ts`).
- Use camelCase for variables, functions, and props (e.g., `const myVariable = 0;`).
- Always place components in their own folders to scope all related files together (tests, subcomponents, stories).

**Component Structure:**

Each component lives in its own folder with the same name, containing the component file, tests, and any related files:

```
src/
  components/
    AuthForm/
      AuthForm.svelte          # Main component file
      AuthForm.test.ts         # Tests for the component
      AuthForm.stories.svelte  # Storybook stories (if needed)
```

**Component with Subcomponents:**

When a component grows complex, split it into subcomponents within the same folder:

```
src/
  components/
    UserDashboard/
      UserDashboard.svelte
      UserDashboard.test.ts
      UserProfile/
        UserProfile.svelte
        UserProfile.test.ts
      UserStats/
        UserStats.svelte
        UserStats.test.ts
```

**Hook Structure:**

Similarly, hooks are stored in their own folders:

```
src/
  lib/
    hooks/
      useAuth/
        useAuth.ts
        useAuth.test.ts
```

## Import/Export Conventions

### Barrel Exports (index.ts)

Use barrel exports via `index.ts` files to create clean, centralized module imports. This approach:

- **Reduces import complexity**: Import from module level instead of deep paths
- **Better change control**: Swap implementations internally without affecting consumers
- **Clear public API**: The `index.ts` explicitly defines what's exported from the module

**Hook Module Structure:**

```
src/
  lib/
    hooks/
      index.ts              # Barrel export file
      useAuth/
        useAuth.ts
        useAuth.test.ts
      useData/
        useData.ts
        useData.test.ts
```

**Barrel Export File (`index.ts`):**

```typescript
// src/lib/hooks/index.ts
export { useAuth } from './useAuth/useAuth';
export { useData } from './useData/useData';
export { useVideo } from './useVideo/useVideo';
```

**Good - Import from module:**

```typescript
// ✅ Good: Import from module level via barrel export
import { useData, useAuth } from "$lib/hooks";
```

**Bad - Import from deep paths:**

```typescript
// ❌ Bad: Deep imports bypass the module's public API
import { useData } from "$lib/hooks/useData/useData";
```

### Absolute vs Relative Imports

- **Use absolute imports** for shared modules (components, hooks, utils):

```typescript
// ✅ Good: Absolute imports for shared code
import { useData } from "$lib/hooks";
import { Button } from "$lib/components/ui/button";
```

- **Use relative imports** only for local files within the same module:

```typescript
// ✅ Good: Relative import within the same component folder
// In: src/components/UserDashboard/UserProfile/UserProfile.svelte
import { formatName } from "../UserDashboard.helpers";
```

**Benefits of this approach:**

- **Cleaner imports**: `from "$lib/hooks"` vs `from "$lib/hooks/useData/useData"`
- **Easier refactoring**: Move files within module without breaking external imports
- **Controlled API surface**: Only export what should be public
- **Better tree-shaking**: Bundlers can optimize based on explicit exports

## TypeScript Usage

- Use TypeScript for all code
- Use interfaces for defining component props and function parameters.
  E.g.:

```typescript
// Hook example
interface UseDataParams {
    title: string;
    onClick: () => void;
}

interface UseDataReturn {
    data: string;
    isLoading: boolean;
}

export function useData(params: UseDataParams): UseDataReturn {
    // ... implementation
    return { data: params.title, isLoading: false };
}

// Component example (see Component Props section for full details)
interface Props {
    title: string;
    onClick: () => void;
}

let { title, onClick }: Props = $props();
```

- Avoid exporting/importing types. Instead, use [TypeScript utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html) to derive types from existing code. This approach:
  - Reduces type duplication
  - Ensures type consistency with the source code
  - Makes refactoring easier as types automatically update with code changes
  - Keeps the codebase DRY (Don't Repeat Yourself)

Common utility type patterns:

```typescript
// Derive parameter types from a function
type UseDataParams = Parameters<typeof useData>[0];

// Derive return type from a function
type UseDataReturn = ReturnType<typeof useData>;

// Make all properties optional
type PartialData = Partial<UseDataParams>;

// Pick specific properties
type TitleOnly = Pick<UseDataParams, "title">;

// Omit specific properties
type WithoutTitle = Omit<UseDataParams, "title">;

// Make all properties required
type RequiredData = Required<Partial<UseDataParams>>;

// Create a type from an object's keys
type DataKeys = keyof UseDataParams;
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
// ✅ Good: Using Shadcn components directly for basic UI elements
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
// ✅ Good: Using project-specific components for complex features
import { DatasetCard, AnnotationToolbar } from '$lib/components';

<DatasetCard dataset={dataset} />
<AnnotationToolbar onSave={handleSave} />
```

#### Component Composition

- When building new components, prefer composition over inheritance
- Use Shadcn components as building blocks for more complex components
- Keep component logic separate from UI elements

```typescript
// ✅ Good: Composing components
<script lang="ts">
  import { Card } from '$lib/components/ui/card';
  import { Button } from '$lib/components/ui/button';
  import { useDataset } from '$lib/hooks';

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
// ❌ Bad: Blind object spreading - unclear what props are actually used
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

// ✅ Good: Explicit props - clear interface and intent
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

## Performance

### Bundle Size and Code Splitting

Keep JavaScript chunk sizes below 500KB to maintain optimal application performance:

- **Why it matters**: Large chunks increase initial page load time, worsen user experience, and can cause performance issues on slower networks or devices.
- **Monitor chunk sizes**: Check build output for warnings about chunk sizes exceeding the 500KB threshold.
- **Code splitting strategies**:
  - Use dynamic imports for routes and large components
  - Lazy load heavy dependencies that aren't needed immediately
  - Split vendor libraries into separate chunks
  - Consider splitting large UI libraries and visualization components

**Example - Dynamic import for code splitting:**

```typescript
// ✅ Good: Lazy load heavy components
<script lang="ts">
  import { onMount } from 'svelte';

  let HeavyChart;

  onMount(async () => {
    const module = await import('$lib/components/HeavyChart.svelte');
    HeavyChart = module.default;
  });
</script>

{#if HeavyChart}
  <svelte:component this={HeavyChart} />
{/if}

// ❌ Bad: Import large components directly
import HeavyChart from '$lib/components/HeavyChart.svelte';
```

**Monitoring chunk sizes:**

```bash
# Build and check chunk sizes
npm run build

# Look for warnings like:
# ⚠ Some chunks are larger than 500KB after minification
```

If you see chunks exceeding 500KB:
1. Identify the large dependencies using build analysis tools
2. Consider lazy loading or splitting the problematic modules
3. Review if all imported dependencies are actually needed
4. Check for duplicate dependencies that could be deduplicated

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
- Use Svelte's props for data passing.
- Leverage Svelte's reactive declarations for local state management.
- Leverage [$app/state](https://svelte.dev/tutorial/kit/page-state) for global state management and access to already loaded data.

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
- Use `src/lib/hooks` for reusable hooks.

### Avoiding Props Drilling

Props drilling occurs when you pass props through multiple component layers just to reach a deeply nested component. This makes code harder to maintain and components tightly coupled.

#### Solution 1: Svelte Context API (Recommended for Component Trees)

Use Svelte's `setContext` and `getContext` for sharing data within a component tree without passing props.

**When to use:**
- Data needed by multiple components in a subtree
- Component-scoped state (e.g., theme, configuration)
- Not needed globally across the entire app

**Example:**

```typescript
// ✅ Good: Using Context API
// ParentComponent.svelte
<script lang="ts">
  import { setContext } from 'svelte';
  import { writable } from 'svelte/store';

  interface UserContext {
    user: { name: string; email: string };
    updateUser: (user: { name: string; email: string }) => void;
  }

  const user = writable({ name: 'John', email: 'john@example.com' });

  setContext<UserContext>('user', {
    user,
    updateUser: (newUser) => user.set(newUser)
  });
</script>

<ChildComponent />

// DeeplyNestedComponent.svelte
<script lang="ts">
  import { getContext } from 'svelte';

  const { user, updateUser } = getContext<UserContext>('user');
</script>

<p>Welcome, {$user.name}!</p>
<button onclick={() => updateUser({ name: 'Jane', email: 'jane@example.com' })}>
  Update User
</button>
```

**Bad - Props drilling:**

```typescript
// ❌ Bad: Passing props through every layer
// ParentComponent.svelte
<script lang="ts">
  const user = { name: 'John', email: 'john@example.com' };
</script>

<MiddleComponent {user} />

// MiddleComponent.svelte
<script lang="ts">
  interface Props {
    user: { name: string; email: string };
  }

  let { user }: Props = $props();
</script>

<AnotherMiddle {user} />

// AnotherMiddle.svelte
<script lang="ts">
  interface Props {
    user: { name: string; email: string };
  }

  let { user }: Props = $props();
</script>

<DeeplyNestedComponent {user} />
```

#### Solution 2: Svelte Stores (For Global State)

Use stores for truly global state that's needed across unrelated parts of the application.

**When to use:**
- Global application state (auth, user preferences)
- State shared across unrelated component trees
- State that persists across navigation

**Example:**

```typescript
// ✅ Good: Using stores for global state
// lib/stores/user.ts
import { writable } from 'svelte/store';

export const currentUser = writable({
  name: 'John',
  email: 'john@example.com'
});

// AnyComponent.svelte
<script lang="ts">
  import { currentUser } from '$lib/stores/user';
</script>

<p>Welcome, {$currentUser.name}!</p>

// AnotherUnrelatedComponent.svelte
<script lang="ts">
  import { currentUser } from '$lib/stores/user';
</script>

<button onclick={() => currentUser.set({ name: 'Jane', email: 'jane@example.com' })}>
  Update User
</button>
```

#### Solution 3: SvelteKit `$app/state` (For Page-Level Data)

Use SvelteKit's page state for data loaded via `+page.ts` or `+page.server.ts`.

**When to use:**
- Data loaded from the server
- Page-specific state that comes from routing
- Data that should be available to all components on a page

**Example:**

```typescript
// ✅ Good: Using page state
// routes/dashboard/+page.ts
export const load = async ({ fetch }) => {
  const user = await fetch('/api/user').then(r => r.json());
  return { user };
};

// routes/dashboard/+page.svelte
<script lang="ts">
  import { page } from '$app/state';
  import UserStats from './UserStats.svelte';
  import UserProfile from './UserProfile.svelte';
</script>

<UserStats />
<UserProfile />

// routes/dashboard/UserProfile.svelte
<script lang="ts">
  import { page } from '$app/state';

  // Access page data directly, no props needed
  const user = page.data.user;
</script>

<p>{user.name}</p>
```

#### Solution 4: Component Composition with Snippets

Sometimes props drilling indicates poor component structure. Use Svelte 5 snippets for flexible component composition.

**Bad - Drilling props for UI customization:**

```typescript
// ❌ Bad: Drilling props for UI customization
<Layout headerText="Dashboard" footerText="© 2024" />
```

**Good - Using Svelte 5 snippets:**

```typescript
// ✅ Good: Using Svelte 5 snippets for reusable content blocks
// Layout.svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    header?: Snippet;
    footer?: Snippet;
    children: Snippet;
  }

  let { header, footer, children }: Props = $props();
</script>

<div class="layout">
  {#if header}
    <header>{@render header()}</header>
  {/if}

  <main>{@render children()}</main>

  {#if footer}
    <footer>{@render footer()}</footer>
  {/if}
</div>

// Usage in parent component
<script lang="ts">
  import Layout from './Layout.svelte';
</script>

<Layout>
  {#snippet header()}
    <h1>Dashboard</h1>
  {/snippet}

  <p>Main content goes here</p>

  {#snippet footer()}
    <p>© 2024</p>
  {/snippet}
</Layout>
```

**Benefits of snippets:**

- **Type-safe**: Snippets are strongly typed with the `Snippet` type
- **Flexible**: Can be passed as props, stored in variables, or conditionally rendered
- **Clear API**: Component interface explicitly shows what content blocks are expected
- **Better composition**: Easier to compose complex layouts without prop drilling

#### Choosing the Right Solution

| Use Case | Solution | Scope |
|----------|----------|-------|
| Component tree state | Context API | Subtree |
| Global app state | Stores | Application-wide |
| Page-loaded data | `$app/state` | Current page |
| UI composition | Slots | Component-specific |

**Best Practices:**

- **Prefer Context API** for component-tree scoped state
- **Use stores sparingly** - only for truly global state
- **Leverage `$app/state`** for server-loaded data instead of prop drilling
- **Consider composition** before reaching for state management
- **Keep context keys type-safe** using TypeScript interfaces

### Svelte 5 Syntax

#### Component Props

Use Svelte 5 `$props()` rune instead of the old `export let` syntax for defining component props.

**Bad Example (Svelte 4):**

```typescript
// ❌ Old Svelte 4 syntax
<script lang="ts">
  export let value: string;
  export let placeholder: string = 'Enter text';
  export let onSearch: (query: string) => void;
  export let disabled: boolean = false;
</script>

<input
  type="text"
  {value}
  {placeholder}
  {disabled}
  onchange={() => onSearch(value)}
/>
```

**Good Example (Svelte 5):**

```typescript
// ✅ Svelte 5 $props() syntax
<script lang="ts">
  interface Props {
    value: string;
    placeholder?: string;
    onSearch: (query: string) => void;
    disabled?: boolean;
  }

  let {
    value,
    placeholder = 'Enter text',
    onSearch,
    disabled = false
  }: Props = $props();
</script>

<input
  type="text"
  {value}
  {placeholder}
  {disabled}
  onchange={() => onSearch(value)}
/>
```

**Benefits of `$props()`:**

- **Type safety**: Props are defined in a clear TypeScript interface
- **Required vs optional**: Interface makes it explicit which props are required
- **Better IDE support**: Autocomplete and type checking work better
- **Destructuring with defaults**: Clear syntax for default values
- **Future-proof**: Aligns with Svelte 5's direction

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

### Passing Reactive Values to Hooks

Avoid passing reactive values to hooks using `$derived`. Hooks should receive stable, non-reactive values as parameters.

#### Best Practice: Pass Data via Page Load Function

Instead of reading reactive values like `page.params` inside components and passing them to hooks, prefer passing data through SvelteKit's load function and accessing it via `$props()`.

**Bad Example - Using `$derived` with hooks:**

```typescript
// ❌ Bad: Using $derived to pass reactive page params to hook
<script lang="ts">
  import { page } from '$app/state';
  import { useVideo } from '$lib/hooks/useVideo';

  const sampleId = $derived(page.params.sample_id);
  const { video } = useVideo({ sampleId });
</script>
```

**Good Example - Pass data through page load:**

```typescript
// ✅ Good: Pass params through page load function
// +page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
  return {
    groupId: url.searchParams.get('group_id') ?? undefined,
    frameNumber: url.searchParams.get('frame_number') ?? undefined,
    params
  };
};

// +page.svelte
<script lang="ts">
  import type { PageData } from './$types';
  import { useVideo } from '$lib/hooks/useVideo';

  const { data }: { data: PageData } = $props();
  const { video } = useVideo({
    sampleId: data.params.sample_id
  });
</script>
```

#### Alternative: Pass Svelte Stores to Hooks

If you need to pass reactive values to hooks, use Svelte stores (`writable`, `readable`, `derived`) instead of `$derived`.

**Bad Example:**

```typescript
// ❌ Bad: Passing $derived value to hook
<script lang="ts">
  import { useAuthInfo } from '$lib/hooks/useAuthInfo';

  const authInfo = $derived(useAuthInfo());
</script>
```

**Good Example:**

```typescript
// ✅ Good: Use the hook directly without $derived
<script lang="ts">
  import { useAuthInfo } from '$lib/hooks/useAuthInfo';

  const { user, isAuthenticated } = useAuthInfo();
</script>

{#if $isAuthenticated}
  <p>Welcome, {$user.name}!</p>
{/if}
```

**Good Example - Using stores when reactivity is needed:**

```typescript
// ✅ Good: If you need reactive parameters, use stores
<script lang="ts">
  import { writable, derived } from 'svelte/store';
  import { useFilteredData } from '$lib/hooks/useFilteredData';

  const searchQuery = writable('');
  const { data } = useFilteredData({ query: searchQuery });
</script>

<input bind:value={$searchQuery} />
{#each $data as item}
  <div>{item.name}</div>
{/each}
```

**Why this matters:**

- **Separation of concerns**: Data fetching logic stays in load functions, not in components
- **Type safety**: PageData types are automatically generated from load functions
- **Better performance**: Data is loaded before the page renders
- **Clearer dependencies**: Hooks receive explicit parameters, not reactive computations
- **Easier testing**: Hooks can be tested with simple values instead of reactive state

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
import { fireEvent } from "@testing-library/svelte";
import MyComponent from "./MyComponent.svelte";

describe("MyComponent with useCounter integration", () => {
  it("increments count when button is clicked", async () => {
    render(MyComponent);
    const button = screen.getByRole("button");

    // Initial state
    expect(button).toHaveTextContent("Count: 0");

    // Click and verify integration
    await fireEvent.click(button);
    expect(button).toHaveTextContent("Count: 1");

    await fireEvent.click(button);
    expect(button).toHaveTextContent("Count: 2");
  });
});
```

### Test Optimization Principles

When writing tests, focus on quality over quantity. Follow these principles to minimize duplication and keep tests maintainable:

#### 1. Use Helper Functions for Repeated Setup

Create `defaultProps` or setup functions to eliminate repeated prop objects:

```typescript
// ✅ Good: DRY approach with defaultProps
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

// ❌ Bad: Repeated prop objects
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

#### 2. Avoid Redundant Mirror Tests

Don't create separate tests for opposite states when both tests exercise the exact same condition. However, test both states if they're controlled by different conditions.

**Good: Test only one state when controlled by a single boolean**

```typescript
// ✅ Good: Testing the truthy case is sufficient
it("disables input when isUploading is true", () => {
  render(SearchInput, { props: { ...defaultProps, isUploading: true } });
  expect(screen.getByRole("textbox")).toBeDisabled();
});

// ❌ Redundant: The opposite case doesn't add coverage
// it("enables input when isUploading is false", () => {
//   render(SearchInput, { props: defaultProps });
//   expect(screen.getByRole("textbox")).not.toBeDisabled();
// });
```

**When to test both states:**

```typescript
// ✅ Good: Test both when different conditions control each state
it("disables button when user lacks permission", () => {
  render(ActionButton, { props: { hasPermission: false, isLoading: false } });
  expect(screen.getByRole("button")).toBeDisabled();
});

it("disables button when loading", () => {
  render(ActionButton, { props: { hasPermission: true, isLoading: true } });
  expect(screen.getByRole("button")).toBeDisabled();
});

it("enables button when user has permission and not loading", () => {
  render(ActionButton, { props: { hasPermission: true, isLoading: false } });
  expect(screen.getByRole("button")).not.toBeDisabled();
});
```

In the second example, all three tests are valuable because:
- Different conditions can cause the disabled state
- The enabled state requires both conditions to be met
- Each test verifies a distinct code path

#### 3. Combine Related Tests

Merge tests that check related functionality:

```typescript
// ✅ Good: Combined test that verifies user-facing behavior
it("renders search input with placeholder and accessible label", () => {
  render(SearchInput, { props: defaultProps });
  expect(screen.getByPlaceholderText("Search")).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveAccessibleName("Search");
});

// ❌ Bad: Separate tests for closely related accessibility features
it("renders search input with placeholder", () => {
  render(SearchInput, { props: defaultProps });
  expect(screen.getByPlaceholderText("Search")).toBeInTheDocument();
});

it("renders search input with accessible label", () => {
  render(SearchInput, { props: defaultProps });
  expect(screen.getByRole("textbox")).toHaveAccessibleName("Search");
});
```

#### 4. Avoid Testing Implementation Details

Don't test internal implementation details like CSS classes or internal structure:

```typescript
// ❌ Bad: Testing CSS classes (implementation detail)
it("renders with correct CSS classes for layout", () => {
  const { container } = render(ActiveSearchDisplay, { props: defaultProps });
  const wrapper = container.querySelector(
    ".flex.h-10.w-full.items-center.rounded-md.border.border-input.bg-background",
  );
  expect(wrapper).toBeInTheDocument();
});

// ✅ Good: Test user-visible behavior instead
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
// ❌ Bad: Testing hook configuration (implementation detail)
it("calls useEmbedText with correct parameters", () => {
  render(GridSearch);
  expect(mockUseEmbedText).toHaveBeenCalledWith({
    collectionId: "test-collection-id",
    queryText: "",
    embeddingModelId: null,
  });
});

// ✅ Good: Test the actual behavior
it("displays search results when query is submitted", async () => {
  render(GridSearch);
  const input = screen.getByRole("textbox");

  await fireEvent.input(input, { target: { value: "test query" } });
  await fireEvent.keyDown(input, { key: "Enter" });

  expect(screen.getByText("test query")).toBeInTheDocument();
});
```

#### 6. Remove Duplicate Tests

Identify and remove tests that verify the same behavior:

```typescript
// ❌ Bad: Both tests check the same thing
it("renders SearchInput when no active search", () => {
  render(GridSearch);
  const input = screen.getByPlaceholderText("Search samples");
  expect(input).toBeInTheDocument();
});

it("shows SearchInput initially", () => {
  render(GridSearch);
  expect(screen.getByTestId("search-input")).toBeInTheDocument();
});

// ✅ Good: One test is sufficient
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
