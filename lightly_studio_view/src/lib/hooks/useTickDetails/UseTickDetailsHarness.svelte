<script lang="ts">
    import { useTickDetails } from './useTickDetails';

    interface Props {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        onReady: (result: ReturnType<typeof useTickDetails>) => void;
    }

    let { datasetId, sequenceId, seqNumber, onReady }: Props = $props();

    const result = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber
    });

    $effect(() => {
        onReady(result);
    });
</script>
