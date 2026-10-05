<script lang="ts">
    import { useTickDetails } from './useTickDetails';

    interface Props {
        datasetId: string;
        sequenceId: string;
        seqNumber: number;
        displayFrameId?: string;
        onReady: (result: ReturnType<typeof useTickDetails>) => void;
    }

    let { datasetId, sequenceId, seqNumber, displayFrameId, onReady }: Props = $props();

    const result = useTickDetails({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId,
        getSeqNumber: () => seqNumber,
        getDisplayFrameId: () => displayFrameId
    });

    $effect(() => {
        onReady(result);
    });
</script>
