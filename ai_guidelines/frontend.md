# Frontend coding guidelines

Coding standards for frontend development in LightlyStudio using SvelteKit and TypeScript.

## Key Principles

- Write concise, technical TypeScript code. Use Svelte-specific features (like runes) only when necessary within Svelte-compiled components.
- Keep components under 100 lines. Split code into logical, testable parts.
- Embrace TDD. Use [vitest](https://vitest.dev/) for unit and integration tests.
- Follow [Svelte](https://svelte.dev/docs) and [SvelteKit](https://kit.svelte.dev/docs) official documentation.

## Framework-agnostic approach

Minimize framework-specific syntax to reduce coupling and improve testability:

- Prefer [writable](https://svelte.dev/docs/svelte/svelte-store)/readable/derived stores over runes for state management - stores have explicit imports and clearer dependencies.
- Use runes only when their specific features are necessary for component-level reactivity.
- Less framework coupling means easier maintenance, onboarding, and migration.

## Project structure & naming

- **PascalCase** for component names and their folders (e.g., `AuthForm/AuthForm.svelte`).
- **camelCase** for non-component files, variables, functions, and props (e.g., `useAuth.ts`, `const myVar`).
- Every component and hook lives in its own folder scoping related files together.

Canonical layout:

```
src/
  components/
    AuthForm/
      AuthForm.svelte
      AuthForm.test.ts
      AuthForm.stories.svelte       # if needed
    UserDashboard/
      UserDashboard.svelte
      UserDashboard.test.ts
      UserDashboard.helpers.ts       # if needed
      UserProfile/                   # subcomponent
        UserProfile.svelte
        UserProfile.test.ts
  lib/
    hooks/
      index.ts                       # barrel exports
      useAuth/
        useAuth.ts
        useAuth.test.ts
      useData/
        useData.ts
        useData.test.ts
```

- Use `.svelte.ts` files for component logic and state machines.
- Use barrel exports (`index.ts`) to define a module's public API. Import from module level, not deep paths:

```typescript
// ✅ from "$lib/hooks"  - not "$lib/hooks/useData/useData"
import { useData, useAuth } from "$lib/hooks";
```

## Imports

- **Absolute imports** for shared modules: `from "$lib/hooks"`, `from "$lib/components/ui/button"`.
- **Relative imports** only within the same module folder: `from "../UserDashboard.helpers"`.

## TypeScript

- Use TypeScript for all code.
- Define `interface` for component props, function parameters, and return types:

```typescript
interface UseDataParams {
  title: string;
  onClick: () => void;
}

interface UseDataReturn {
  data: string;
  isLoading: boolean;
}

export function useData(params: UseDataParams): UseDataReturn {
  return { data: params.title, isLoading: false };
}
```

- Avoid exporting/importing types. Derive types from source code using utility types to keep things DRY:

```typescript
type UseDataParams = Parameters<typeof useData>[0];
type UseDataReturn = ReturnType<typeof useData>;
type TitleOnly = Pick<UseDataParams, "title">;
type WithoutTitle = Omit<UseDataParams, "title">;
```

## UI and Styling

- **[Shadcn](https://next.shadcn-svelte.com/)** components from `$lib/components/ui` for standard UI elements (buttons, inputs, cards, tabs, alerts, tables).
- **Project-specific components** from `$lib/components` when combining multiple Shadcn components, adding business logic, or needing custom behavior.
- **[Bits-UI](https://www.bits-ui.com/)** as the base component library underlying Shadcn.
- **[Lucide Icons](https://lucide.dev/icons/)** for all icons - import from `@lucide/svelte`.
- Use `cn()` from `$lib/utils` for conditional Tailwind class composition.
- Prefer explicit props over object spreading - components should receive only the specific props they need. Exception: forwarding HTML attributes via `...rest`, or intentional wrapper/proxy components.

## Performance

Keep JS chunk sizes **below 500KB**. Use dynamic imports for heavy components:

```typescript
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
```

When reviewing bundle size:

- Check build output for chunk-size warnings.
- Identify heavy dependencies before adding them to eagerly loaded routes.
- Prefer lazy loading, vendor splitting, or dependency deduplication when a chunk exceeds the limit.

## Svelte 5 syntax

Use Svelte 5 patterns in all new code:

**Props** - use `$props()` with a typed interface:

```typescript
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
```

**Event handlers** - use `onclick`, `onchange`, etc. (not `on:click`, `on:change`).

**Reactive declarations** - use `$derived` or `derived()` stores, not `$:`. Do not mix the two approaches - pick one per file/module.

**Page state** - use `$app/state`, not `$app/stores`:

```typescript
import { page } from "$app/state";
page.params.sampleId; // no $ prefix needed
```

**Hooks and reactivity** - do not pass `$derived` values to hooks. Pass stable values via SvelteKit's page load function or stores:

```typescript
// +page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
  return {
    groupId: url.searchParams.get('group_id') ?? undefined,
    params
  };
};

// +page.svelte
<script lang="ts">
  import type { PageData } from './$types';
  import { useVideo } from '$lib/hooks/useVideo';

  const { data }: { data: PageData } = $props();
  const { video } = useVideo({ sampleId: data.params.sample_id });
</script>
```

If you need reactive parameters in a hook, pass Svelte stores (`writable`/`derived`), not `$derived` rune values.

## State management & hooks

Create small, reusable hooks in `src/lib/hooks` - avoid monolithic stores. We do not use a `services` folder; hooks handle data fetching and state.
Ref: [useTags](../../lightly_studio_view/src/lib/hooks/useTags/useTags.ts), [useFeatureFlags](../../lightly_studio_view/src/lib/hooks/useFeatureFlags/useFeatureFlags.ts).

Generic hooks go in `src/lib/hooks`; component-specific hooks go in the component's folder.

For data fetching and API work:

- Use hooks for client-side data fetching unless there is a specific reason to introduce a service.
- Implement proper error handling for data fetching operations.
- Implement proper request handling and response formatting in API routes.

**Hook pattern example:**

```typescript
import { writable } from 'svelte/store';

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

**Store-based hook example** ([playground](https://svelte.dev/playground/hello-world?version=5.32.1#H4sIAAAAAAAAE3WRwW6DMBBEf2W1qhSioqS9koBU9TNKD8TZVFZhjex1kwr53yvjhkCVXjisZ2aHtwNy0xEW6B29Gs9CFujSdH1LmONJt-SweBtQvvuoigPMr56Xvt-4L2olzg6No3tzZViIxWGBe6es7gXahj_KGsXVWNUMAKC73liBAWY1Apys6WC12d6GG3GrXc3JpAy76FHxLQfNylJHLBCgnAVl613N-23aXUXz_uBFDINh1Wr1WQ7ZGsrqFpAtw2-vMaKA4WHcEWJO8lY1Y45CF8FCrKeQ_8No0X2J6e_TjNTE42y1NIeWJhqJ69aJsZRQJAxjQSgnw559dyBbZU_rUUWXMfHkWYk2vOADQ_rb9J0kMx5XRcLuWTa-PzZCWaZGdAoe4TkuioJwPdCUZMmRjOvuRTmS1HJhtiTe8p3z5rM4CLuaw_IS7zlKo9uz5iMWp6Z1FH4Aaa7hNOYCAAA=)):

```typescript
// useCounter.ts
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

// Counter.svelte
<script lang="ts">
  import { useCounter } from './useCounter';
  const { count, increment } = useCounter();
</script>

<button onclick={() => increment()}>Count: {$count}</button>
```

### Avoiding props drilling

Prefer these solutions in order:

1. **Svelte Context API** (`setContext`/`getContext`) - for state shared within a component subtree.
2. **Svelte stores** - for truly global state (auth, preferences) shared across unrelated trees.
3. **`$app/state`** - for server-loaded page data accessible by any component on the page.
4. **Svelte 5 Snippets** (`Snippet` type) - for UI composition / layout customization without passing content as props.

## Routing and Pages

- Use [SvelteKit's file-based routing](https://svelte.dev/tutorial/kit/layouts) in `src/routes/`.
- Use dynamic routes with [slug](https://svelte.dev/tutorial/kit/params) syntax. E.g. [sample details](../../lightly_studio_view/src/routes/samples/[sample_id]/).
- Use `+layout.svelte` for shared layouts. E.g. [collections layout](../../lightly_studio_view/src/routes/collections/[collection_id]/+layout.svelte).

## Storybook

Use simplified story syntax - no explicit `{#snippet children()}` for text content:

```typescript
<Story name="H1" args={{ variant: 'h1' }}>
    Heading 1 - Large Page Title
</Story>
```

## Testing

**Testing levels:** Unit tests for isolated components/functions, integration tests for component interactions, end-to-end tests for full application flows.

**Unit test example:**

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

### Test optimization rules

- **Use `defaultProps`** helper objects to avoid repeating prop definitions across tests. Override individual props with spread: `{ ...defaultProps, isUploading: true }`.
- **No mirror tests** for simple boolean toggles - testing the truthy case is sufficient when a single boolean controls the state.
- **Combine related assertions** into one test rather than creating separate tests for closely related checks (e.g., placeholder + accessible label).
- **Test behavior, not implementation** - don't assert on CSS classes, internal structure, or how hooks are called. Assert on user-visible outcomes.
- **Remove duplicate tests** that verify the same behavior with different queries.

### Running tests

Before submitting code:

```bash
# Static checks (TypeScript, ESLint, Prettier, Svelte check)
make static-checks

# Unit tests
npm run test:unit
```

All checks must pass before committing.
