<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { useMcapTickPrefetchScheduler } from './useMcapTickPrefetchScheduler.svelte';

    interface Props {
        ticks: TickView[];
        ranges: { startIndex: number; endIndex: number }[];
        requestId?: string;
        onReady: (result: ReturnType<typeof useMcapTickPrefetchScheduler>) => void;
    }

    let { ticks, ranges, requestId = 'test', onReady }: Props = $props();
    const result = useMcapTickPrefetchScheduler({
        getDatasetId: () => 'dataset-1',
        getSequenceId: () => 'sequence-1',
        getDisplayFrameId: () => 'base_link',
        getTicks: () => ticks,
        getRequestId: () => requestId,
        getRanges: () => ranges,
        getChunkSize: () => 2,
        getDelayMs: () => 100
    });

    $effect(() => onReady(result));
</script>
