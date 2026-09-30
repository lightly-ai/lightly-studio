<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useSimilarityRange } from '$lib/hooks/useSimilarityRange';
    import SimilarityThresholdSlider from './SimilarityThresholdSlider/SimilarityThresholdSlider.svelte';

    interface Props {
        collectionId: string;
        textEmbedding: number[];
        value: number | null;
        onCommit: (value: number) => void;
        onClear: () => void;
    }

    const { collectionId, textEmbedding, value, onCommit, onClear }: Props = $props();

    const rangeQuery = useSimilarityRange(() => ({ collectionId, textEmbedding }));
</script>

{#if rangeQuery.data}
    <Segment title="Similarity search threshold">
        <SimilarityThresholdSlider range={rangeQuery.data} {value} {onCommit} {onClear} />
    </Segment>
{/if}
