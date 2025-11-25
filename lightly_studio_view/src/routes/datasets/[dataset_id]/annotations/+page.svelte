<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { PageData } from './$types';
    import { useTags } from '$lib/hooks/useTags/useTags';

    const { data }: { data: PageData } = $props();
    const { datasetId, sampleSize, selectedAnnotationFilterIds, rootDatasetId } = data;

    const { lastGridType } = useGlobalStorage();

    // Use root dataset ID for tags - tags should always use root dataset, not child datasets
    const tagsDatasetId = rootDatasetId ?? datasetId;

    const { clearTagsSelected } = $derived(
        useTags({
            dataset_id: tagsDatasetId
        })
    );

    $effect(() => {
        if ($lastGridType !== 'annotations') {
            clearTagsSelected();
        }
    });
</script>

<AnnotationsGrid
    itemWidth={$sampleSize.width}
    dataset_id={datasetId}
    rootDatasetId={rootDatasetId}
    {selectedAnnotationFilterIds}
/>