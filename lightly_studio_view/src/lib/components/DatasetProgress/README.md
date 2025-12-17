# Dataset Progress Tracking System

A comprehensive UI progress tracking system for monitoring dataset processing operations (indexing, embedding generation, etc.).

## Features

- ✅ **Progress Bar Component** with visual states (pending, indexing, embedding, ready, error)
- ✅ **Compact Header Variant** optimized for navigation bar display
- ✅ **HTTP Polling** for progress updates with configurable intervals
- ✅ **WebSocket Support** for real-time progress updates with automatic fallback to polling
- ✅ **Svelte Store Integration** using hooks pattern
- ✅ **Mock Data** for testing and development
- ✅ **TypeScript** with full type safety
- ✅ **Automatic Cleanup** to prevent memory leaks
- ✅ **Integrated in Header** - automatically shows when dataset is processing

## Quick Start

### Basic Usage

```svelte
<script lang="ts">
    import { DatasetProgress } from '$lib/components/DatasetProgress';
    import { useDatasetProgress } from '$lib/hooks/useDatasetProgress';

    const dataset_id = 'my-dataset-id';
    const { progress, startProgress } = useDatasetProgress({
        dataset_id,
        mode: 'polling' // or 'websocket' or 'manual'
    });

    // Start tracking progress
    startProgress();
</script>

{#if $progress}
    <DatasetProgress
        state={$progress.state}
        current={$progress.current}
        total={$progress.total}
        message={$progress.message}
        error={$progress.error}
    />
{/if}
```

## Components

### DatasetProgress Component

Main progress bar component with animated states.

**Props:**
- `state` (required): `'pending' | 'indexing' | 'embedding' | 'ready' | 'error'`
- `current` (optional): Current progress value (default: 0)
- `total` (optional): Total value (default: 100)
- `message` (optional): Status message to display
- `error` (optional): Error message to display

**Example:**
```svelte
<DatasetProgress
    state="indexing"
    current={45}
    total={100}
    message="Processing samples..."
/>
```

### DatasetProgressCompact Component

Compact variant optimized for headers and tight spaces. **Already integrated in the Header component!**

**Props:**
- `state` (required): `'pending' | 'indexing' | 'embedding' | 'ready' | 'error'`
- `current` (optional): Current progress value (default: 0)
- `total` (optional): Total value (default: 100)

**Features:**
- Smaller size (fits in navigation bar)
- Simplified display (no messages)
- Thin progress bar (1px instead of 2.5px)
- Abbreviated labels ("Processing" instead of "Generating Embeddings")

**Example:**
```svelte
<DatasetProgressCompact
    state="embedding"
    current={75}
    total={100}
/>
```

### Header Integration

The progress indicator is **automatically displayed** in the header when:
- A dataset is being processed (state is `indexing` or `embedding`)
- You're on a dataset page (URL contains `/datasets/[dataset_id]`)

The Header component:
- Automatically starts polling for progress updates
- Shows the compact progress indicator
- Cleans up when navigating away
- Uses HTTP polling with 3-second intervals

**No additional setup required!** Just ensure the backend progress API is available.

## Hooks

### useDatasetProgress Hook

Hook for managing dataset progress state with automatic API integration.

**Options:**
```typescript
interface UseDatasetProgressOptions {
    dataset_id: string;
    mode?: 'polling' | 'websocket' | 'manual';  // default: 'polling'
    pollingInterval?: number;  // default: 2000ms
}
```

**Returns:**
```typescript
interface UseDatasetProgressReturn {
    progress: Readable<DatasetProgress | null>;
    startProgress: () => void;
    stopProgress: () => void;
    updateProgress: (current: number, total: number, message?: string) => void;
    setError: (error: string) => void;
    setReady: () => void;
    isLoading: Readable<boolean>;
    error: Readable<string | null>;
}
```

**Modes:**

1. **Polling Mode** (Recommended for now)
   - Uses HTTP polling to fetch progress updates
   - Automatically stops when dataset is ready or errors
   ```svelte
   const { progress, startProgress } = useDatasetProgress({
       dataset_id: 'my-dataset',
       mode: 'polling',
       pollingInterval: 3000  // Poll every 3 seconds
   });
   ```

2. **WebSocket Mode** (For future real-time updates)
   - Establishes WebSocket connection for real-time updates
   - Automatically falls back to polling if WebSocket fails
   - Auto-reconnection with configurable attempts
   ```svelte
   const { progress, startProgress } = useDatasetProgress({
       dataset_id: 'my-dataset',
       mode: 'websocket'
   });
   ```

3. **Manual Mode** (For testing)
   - No automatic updates, you control everything
   ```svelte
   const { progress, updateProgress } = useDatasetProgress({
       dataset_id: 'my-dataset',
       mode: 'manual'
   });

   // Manually update progress
   updateProgress(50, 100, 'Halfway there!');
   ```

## API Integration

### HTTP Polling (Current Implementation)

The system uses HTTP polling with a mock implementation. Replace the mock in `progressApi.ts` when the backend is ready:

```typescript
// Current (Mock):
export async function fetchDatasetProgress(dataset_id: string): Promise<DatasetProgress | null> {
    return mockFetchProgress(dataset_id);
}

// Replace with:
export async function fetchDatasetProgress(dataset_id: string): Promise<DatasetProgress | null> {
    const response = await client.GET('/api/datasets/{dataset_id}/progress', {
        params: { path: { dataset_id } }
    });

    if (response.error) {
        throw new Error(`Failed to fetch progress: ${JSON.stringify(response.error)}`);
    }

    return response.data;
}
```

### WebSocket (Future Implementation)

WebSocket endpoint expected at: `ws://[API_URL]/api/datasets/{dataset_id}/progress/ws`

**Message Format:**
```typescript
// Subscribe
{ type: 'subscribe', dataset_id: string }

// Progress Update (received)
{
    type: 'progress_update',
    payload: DatasetProgress
}

// Error (received)
{ type: 'error', message: string }

// Unsubscribe
{ type: 'unsubscribe', dataset_id: string }
```

## Testing

### Demo Component

Use the demo component to test the progress system:

```svelte
<script>
    import { DatasetProgressDemo } from '$lib/components/DatasetProgress/DatasetProgressDemo.svelte';
</script>

<DatasetProgressDemo dataset_id="test-dataset" mode="manual" />
```

### Simulate Progress

For testing purposes, you can simulate progress updates:

```typescript
import { simulateProgress } from '$lib/hooks/useDatasetProgress';

// Start simulation (auto-increments progress)
const cleanup = simulateProgress('my-dataset', () => {
    console.log('Progress complete!');
});

// Stop simulation when done
cleanup();
```

## File Structure

```
DatasetProgress/
├── DatasetProgress.svelte          # Main progress component
├── DatasetProgressDemo.svelte      # Demo/testing component
├── types.ts                        # TypeScript definitions
├── index.ts                        # Exports
└── README.md                       # This file

hooks/
└── useDatasetProgress/
    ├── useDatasetProgress.ts       # Main hook implementation
    └── index.ts

services/
└── progress/
    ├── progressApi.ts              # HTTP polling implementation
    ├── websocket.ts                # WebSocket client
    └── index.ts
```

## Integration Examples

### In a Dataset View Page

```svelte
<script lang="ts">
    import { page } from '$app/stores';
    import { DatasetProgress } from '$lib/components/DatasetProgress';
    import { useDatasetProgress } from '$lib/hooks/useDatasetProgress';
    import { onMount, onDestroy } from 'svelte';

    const dataset_id = $page.params.dataset_id;

    const {
        progress,
        startProgress,
        stopProgress,
        isLoading
    } = useDatasetProgress({
        dataset_id,
        mode: 'polling',
        pollingInterval: 2000
    });

    onMount(() => {
        // Start tracking progress when component mounts
        startProgress();
    });

    onDestroy(() => {
        // Clean up when component unmounts
        stopProgress();
    });
</script>

<div class="dataset-view">
    <h1>Dataset: {dataset_id}</h1>

    {#if $progress && $progress.state !== 'ready'}
        <div class="progress-section">
            <DatasetProgress
                state={$progress.state}
                current={$progress.current}
                total={$progress.total}
                message={$progress.message}
                error={$progress.error}
            />
        </div>
    {:else if $progress?.state === 'ready'}
        <!-- Show dataset content -->
        <div class="dataset-content">
            Dataset is ready! Show samples here...
        </div>
    {/if}
</div>
```

### Multiple Dataset Progress

Track progress for multiple datasets simultaneously:

```svelte
<script lang="ts">
    import { DatasetProgress } from '$lib/components/DatasetProgress';
    import { useDatasetProgress } from '$lib/hooks/useDatasetProgress';

    const datasets = ['dataset-1', 'dataset-2', 'dataset-3'];

    // Create progress hooks for each dataset
    const progressHooks = datasets.map(id => ({
        id,
        hook: useDatasetProgress({ dataset_id: id, mode: 'polling' })
    }));

    // Start all
    progressHooks.forEach(({ hook }) => hook.startProgress());
</script>

<div class="datasets-grid">
    {#each progressHooks as { id, hook }}
        <div class="dataset-card">
            <h3>{id}</h3>
            {#if $hook.progress}
                <DatasetProgress
                    state={$hook.progress.state}
                    current={$hook.progress.current}
                    total={$hook.progress.total}
                    message={$hook.progress.message}
                />
            {/if}
        </div>
    {/each}
</div>
```

## Customization

### Custom Styling

The progress bar uses Tailwind CSS classes. You can customize colors and animations by modifying the component:

```svelte
<!-- Custom color scheme -->
<DatasetProgress
    state="indexing"
    current={50}
    total={100}
    class="custom-progress"
/>

<style>
    :global(.custom-progress .progress-bar) {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
</style>
```

## Backend Requirements

When implementing the backend, ensure these endpoints are available:

1. **GET** `/api/datasets/{dataset_id}/progress`
   - Returns current progress state
   - Response: `DatasetProgress` object

2. **WebSocket** `/api/datasets/{dataset_id}/progress/ws` (optional)
   - Real-time progress updates
   - Messages follow format in "WebSocket" section above

## Troubleshooting

### Progress Not Updating
- Check browser console for errors
- Verify `dataset_id` is correct
- Check network tab for API calls (in polling mode)
- Ensure `startProgress()` was called

### WebSocket Connection Fails
- System automatically falls back to polling
- Check WebSocket URL in browser console
- Verify backend WebSocket endpoint is running

### Memory Leaks
- Always call `stopProgress()` in `onDestroy` or cleanup
- Demo component includes proper cleanup examples

## Future Enhancements

- [ ] Pause/Resume functionality
- [ ] Progress history tracking
- [ ] Estimated time remaining
- [ ] Notification on completion
- [ ] Progress persistence across page reloads
- [ ] Batch progress tracking
- [ ] Custom progress stages beyond indexing/embedding

## Support

For issues or questions, contact the Lightly Studio team or file an issue in the repository.
