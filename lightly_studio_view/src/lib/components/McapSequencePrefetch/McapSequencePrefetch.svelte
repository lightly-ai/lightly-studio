<script lang="ts">
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
    const { summary } = useMcapSequenceSummary({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });
    const { ticks } = useMcapSequenceTicks({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });
    const getDefaultFrameId = () =>
        summary.data?.reference_frames.find((frame) => frame.name === 'CABIN')?.name ??
        summary.data?.reference_frames[0]?.name;

    // The scheduler starts as soon as the tick list is available and stores all results in the
    // same cache used by the labeling workspace. It intentionally renders no visible UI.
    useMcapTickPrefetchScheduler({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
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
