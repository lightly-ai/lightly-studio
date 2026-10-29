<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    import { page } from '$app/state';

    const collectionId = $derived(page.params.collection_id!);

    const { sampleSize } = useGlobalStorage();
</script>

<AnnotationsGrid itemWidth={$sampleSize.width} collection_id={collectionId} />
