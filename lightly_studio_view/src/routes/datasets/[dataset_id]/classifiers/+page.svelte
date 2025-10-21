<script lang="ts">
    import { Samples } from '$lib/components/index.js';

    const { data } = $props();
    const {
        datasetId: dataset_id,
        sampleSize,
        selectedAnnotationFilterIds,
        globalStorage: { textEmbedding }
    } = data;
</script>

<Samples
    sampleHeight={$sampleSize.height}
    sampleWidth={$sampleSize.width}
    {textEmbedding}
    {dataset_id}
    {selectedAnnotationFilterIds}
/>
