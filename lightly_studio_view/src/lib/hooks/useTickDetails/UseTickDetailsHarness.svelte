<script lang="ts">
    import { useTickDetails } from './useTickDetails';

    interface Props {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        targetFrameId?: string;
        onReady: (result: ReturnType<typeof useTickDetails>) => void;
    }

    let { datasetId, sequenceId, seqNumber, targetFrameId, onReady }: Props = $props();

    const result = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber,
        getTargetFrameId: () => targetFrameId
    });

    $effect(() => {
        onReady(result);
    });
</script>
