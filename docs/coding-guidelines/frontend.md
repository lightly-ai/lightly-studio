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
import { useData } from '$lib/hooks/useData';
```
instead of:
```typescript
import { useData } from '../../../lib/hooks/useData';
```

- Use relative imports only for local files. Example:
```typescript
import { useData } from './useData';
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
type TitleOnly = Pick<UseDataProps, 'title'>;

// Omit specific properties
type WithoutTitle = Omit<UseDataProps, 'title'>;

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

- Organize Tailwind classes using the `cn()` utility from `$lib/utils`. This utility helps combine Tailwind classes conditionally and prevents class conflicts.


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


## State Management
- use reusable tiny hooks to avoid one big store for all the state management. E.g. [useTags](../../lightly_studio_view/src/lib/hooks/useTags/useTags.ts).
- Separate state management logic from the component logic as much as possible for better maintanance. Use `src/lib/hooks` for reusable hooks.


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
- Use +layout.svelte for shared layout components. E.g. [shared layout for samples/annotations Grid](../../lightly_studio_view/src/routes/datasets/[dataset_id]/+layout.svelte).


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
      const response = await fetch('/api/users');
      const data = await response.json();
      users.set(data);
    } catch (err) {
      error.set(err instanceof Error ? err : new Error(String(err)));
    } finally {
      isLoading.set(false);
    }
  }
  
  return { data:users, isLoading, error, fetchUsers };
}
```


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
import { render, screen } from '@testing-library/svelte';
import MyComponent from './MyComponent.svelte';

describe('MyComponent', () => {
    it('renders the title', () => {
        render(MyComponent, { props: { title: 'Hello World' } });
        expect(screen.getByText('Hello World')).toBeInTheDocument();
    });
});
```

##### Integration tests
To test the interaction between components and functions. It tests the integration of multiple components and their interactions with each other.

```typescript
import { render, screen } from '@testing-library/svelte';
import MyComponent from './MyComponent.svelte';
import { fireEvent } from '@testing-library/svelte';
import { useCounter } from './useCounter.ts';
 
describe('MyComponent calls useCounter', () => {
    it('calls the increment function when clicked', async () => {
        const { increment } = useCounter();
        const incrementSpy = jest.spyOn(increment, 'increment');
        render(MyComponent);
        await fireEvent.click(screen.getByRole('button'));
        expect(incrementSpy).toHaveBeenCalled();
    });
});
```
