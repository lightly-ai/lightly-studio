<script lang="ts">
    import { useMcapSequenceTicks } from './useMcapSequenceTicks.svelte';

    interface Props {
        datasetId: string;
        sequenceId: string;
        onReady: (result: ReturnType<typeof useMcapSequenceTicks>) => void;
    }

    let { datasetId, sequenceId, onReady }: Props = $props();
    const result = useMcapSequenceTicks({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });

    $effect(() => onReady(result));
</script>
