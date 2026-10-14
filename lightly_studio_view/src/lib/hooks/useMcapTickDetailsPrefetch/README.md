# MCAP tick prefetching

This folder contains the building blocks for buffering MCAP sequence ticks.

## Responsibilities

`prefetchMcapTick` loads the data required by one tick:

- tick details, including annotations;
- point-cloud frames;
- camera frames.

The results are stored in the same caches used by the visible workspace. Tick details and point
clouds use TanStack Query. Camera frames are requested with the same URL used by the camera image,
so the browser can reuse the response from its HTTP cache.

`useMcapTickDetailsPrefetch` is the low-level range executor. It owns request concurrency and
reports completed ranges, but it does not decide when or why a range should be loaded.

`useMcapTickPrefetchScheduler` is the policy layer. It splits ranges into chunks and waits between
chunks. It is the appropriate hook for initial loading, marked-tick loading, and direct jumps.

## Using the range executor

Use a stable `requestId` for one buffering session. Calling `prefetchRanges` with a new request ID
starts a new session and discards queued work from the previous session. In-flight network requests
finish in the background, but their results are ignored by the old session.

```svelte
<script lang="ts">
    import { useMcapTickDetailsPrefetch } from '$lib/hooks';

    const ticks = $derived(sequenceTicks.data?.ticks ?? []);
    const { bufferedRanges, prefetchRanges, cancel } = useMcapTickDetailsPrefetch({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getDisplayFrameId: () => displayFrameId,
        getTicks: () => ticks
    });

    async function loadRange(startIndex: number, endIndex: number) {
        await prefetchRanges({
            requestId: 'sequence-initial-load',
            ranges: [{ startIndex, endIndex }]
        });
    }
</script>
```

The executor limits work to four concurrent tick requests. Use the scheduler when chunks and
delays are part of the behavior.

## Using the scheduler

The scheduler keeps timing and prioritization separate from range execution:

```svelte
<script lang="ts">
    import { useMcapTickPrefetchScheduler } from '$lib/hooks';

    const startIndex = $derived(Math.max(0, currentIndex));
    const endIndex = $derived(Math.min(ticks.length - 1, startIndex + 49));
    const { bufferedRanges } = useMcapTickPrefetchScheduler({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getDisplayFrameId: () => displayFrameId,
        getTicks: () => ticks,
        // Keep this stable while playback advances. Change it only for a jump or a new sequence.
        getRequestId: () => 'playback-session',
        getRanges: () => [{ startIndex, endIndex }],
        getChunkSize: () => 10,
        getDelayMs: () => 200
    });
</script>

<!-- The workspace colors buffered tick marks directly on its timeline ruler. -->
```

`bufferedRanges` is updated after each successfully prefetched tick. `errors` contains failed tick
indexes and the original errors for logging or future UI display:

```svelte
<script lang="ts">
    const { bufferedRanges, errors } = useMcapTickPrefetchScheduler(/* ... */);

    $effect(() => {
        for (const [index, error] of errors) {
            console.error(`Could not prefetch MCAP tick ${index}`, error);
        }
    });
</script>
```

The hook is a background cache warmer. The workspace keeps a moving look-ahead window around the
active tick; its default size is 50 ticks and it can be changed with `prefetchTickCount`. During
playback, the window moves forward as the active tick changes, so the next ticks are loaded before
they are shown. Playback pauses when the active tick is not in `bufferedRanges` and resumes after
prefetching completes. The visible queries still provide a second readiness check for the tick
details and point-cloud frame.

### Initial loading

Mount the scheduler in the workspace component and start its range at the tick selected in the Grid.
The selected tick can be loaded alone or with a look-ahead window:

```ts
const initialIndex = $derived(
    Math.max(0, ticks.findIndex((tick) => tick.seq_number === initialTick))
);

getRequestId: () => `${datasetId}/${sequenceId}/initial`,
getRanges: () => [{ startIndex: initialIndex, endIndex: initialIndex + 9 }];
```

The same TanStack Query cache is used by the visible workspace, so opening the initial tick can reuse
the prefetched details and point cloud.

### Loading from a marked tick

Start the ranges at the marked tick and use a request ID containing that position. This makes the
marked position the beginning of a new buffering session:

```ts
getRequestId: () => `marked-${markedIndex}`;
```

### Jumping to a target range

Change the request ID when the user jumps. The scheduler cancels the old plan and prioritizes the
new ranges.

```ts
getRequestId: () => `jump-${targetStart}-${targetEnd}`;
```

### Continuous playback

Keep `requestId` stable while playback advances. Update only `getRanges` to move the look-ahead
window forward:

```ts
getRequestId: () => `${datasetId}/${sequenceId}/playback`,
getRanges: () => [
    {
    startIndex: Math.max(0, currentIndex),
        endIndex: Math.min(ticks.length - 1, currentIndex + 50)
    }
];
```

Changing `requestId` resets `bufferedRanges` and `errors`. Changing ranges with the same request ID
keeps completed ticks and adds only the new work.

Annotations do not need a separate local cache. They are part of the tick-details query and are
available from the same TanStack Query cache when the visible tick is opened.
