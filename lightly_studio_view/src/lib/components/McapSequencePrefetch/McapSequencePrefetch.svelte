<script lang="ts">
    import { onMount } from 'svelte';
    import { useMcapSequenceSummary } from '$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary';
    import { useMcapSequenceTicks } from '$lib/hooks/useMcapSequenceTicks/useMcapSequenceTicks.svelte';
    import { useMcapTickPrefetchScheduler } from '$lib/hooks/useMcapTickDetailsPrefetch/useMcapTickPrefetchScheduler.svelte';

    interface Props {
        /** Dataset containing the MCAP sequence. */
        datasetId: string;
        /** MCAP sequence whose first ticks should be warmed in the cache. */
        sequenceId: string;
    }

    let { datasetId, sequenceId }: Props = $props();
    let isPrefetchEnabled = $state(false);

    onMount(() => {
        let idleCallbackId: number | undefined;
        const idleWindow = window as typeof window & {
            requestIdleCallback?: (callback: () => void) => number;
            cancelIdleCallback?: (id: number) => void;
        };
        const startPrefetch = () => {
            idleCallbackId = undefined;
            isPrefetchEnabled = true;
        };
        const schedulePrefetch = () => {
            if (document.visibilityState !== 'visible' || idleCallbackId !== undefined) return;
            if (!idleWindow.requestIdleCallback) return;
            idleCallbackId = idleWindow.requestIdleCallback(startPrefetch);
        };
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'hidden' && idleCallbackId !== undefined) {
                idleWindow.cancelIdleCallback?.(idleCallbackId);
                idleCallbackId = undefined;
            }
            schedulePrefetch();
        };

        // Do not fall back to a timer: timers can run in background tabs and compete with
        // navigation. Prefetching is an optional optimization, so unsupported browsers skip it.
        if (!idleWindow.requestIdleCallback) return;
        document.addEventListener('visibilitychange', handleVisibilityChange);
        schedulePrefetch();

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            if (idleCallbackId !== undefined) idleWindow.cancelIdleCallback?.(idleCallbackId);
        };
    });

    const { summary } = useMcapSequenceSummary({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getEnabled: () => isPrefetchEnabled
    });
    const { ticks } = useMcapSequenceTicks({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getEnabled: () => isPrefetchEnabled
    });
    const getDefaultFrameId = () =>
        summary.data?.reference_frames.find((frame) => frame.name === 'CABIN')?.name ??
        summary.data?.reference_frames[0]?.name;

    // The scheduler starts as soon as the tick list is available and stores all results in the
    // same cache used by the labeling workspace. It intentionally renders no visible UI.
    useMcapTickPrefetchScheduler({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getEnabled: () => isPrefetchEnabled,
        // Match the labeling workspace's default: it prefers CABIN and otherwise uses the
        // first frame from the sequence summary. This makes targeted tick-details and point-cloud
        // cache keys reusable when the sequence is opened from the grid.
        getDisplayFrameId: getDefaultFrameId,
        getTicks: () => ticks.data?.ticks ?? [],
        // Include the frame in the session id so the scheduler restarts when summary data reveals
        // the default frame after the tick list arrives.
        getRequestId: () => `grid/${datasetId}/${sequenceId}/${getDefaultFrameId() ?? 'sensor'}`,
        getRanges: () => [{ startIndex: 0, endIndex: 49 }]
    });
</script>
