<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { useMcapTickDetailsPrefetch } from './useMcapTickDetailsPrefetch.svelte';

    interface Props {
        ticks: TickView[];
        ranges: { startIndex: number; endIndex: number }[];
        onReady: (result: ReturnType<typeof useMcapTickDetailsPrefetch>) => void;
    }

    let { ticks, ranges, onReady }: Props = $props();
    const result = useMcapTickDetailsPrefetch({
        getDatasetId: () => 'dataset-1',
        getSequenceId: () => 'sequence-1',
        getDisplayFrameId: () => 'base_link',
        getTicks: () => ticks
    });

    $effect(() => onReady(result));
    $effect(() => {
        void result.prefetchRanges({ requestId: 'test', ranges });
    });
</script>
