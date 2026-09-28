<script lang="ts">
    import { useSequenceTicks } from './useSequenceTicks';

    interface Props {
        datasetId: string;
        sequenceId: string;
        onReady: (result: ReturnType<typeof useSequenceTicks>) => void;
    }

    let { datasetId, sequenceId, onReady }: Props = $props();

    const result = useSequenceTicks({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });

    $effect(() => {
        onReady(result);
    });
</script>
