<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { PageData } from './$types';
    import { useTags } from '$lib/hooks/useTags/useTags';

    const { data }: { data: PageData } = $props();
    const { datasetId, sampleSize, selectedAnnotationFilterIds } = data;

    const { lastGridType } = useGlobalStorage();

    const { clearTagsSelected } = $derived(
        useTags({
            dataset_id: datasetId
        })
    );

    $effect(() => {
        if ($lastGridType !== 'annotations') {
            clearTagsSelected();
        }
    });
</script>

<AnnotationsGrid
    itemHeight={$sampleSize.height}
    itemWidth={$sampleSize.width}
    dataset_id={datasetId}
    {selectedAnnotationFilterIds}
/>
