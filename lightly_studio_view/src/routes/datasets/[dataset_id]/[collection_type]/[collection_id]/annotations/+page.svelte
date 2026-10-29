<script lang="ts">
    import { AnnotationsGrid } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    import { page } from '$app/state';
    import { useOpenSample } from '$lib/hooks/useOpenSample/useOpenSample';

    const collectionId = $derived(page.params.collection_id!);

    const { sampleSize } = useGlobalStorage();

    // Back on the grid means the details view was closed, so the tab opens on the grid again.
    const { forgetOpenSample } = useOpenSample();
    $effect(() => forgetOpenSample(collectionId));
</script>

<AnnotationsGrid itemWidth={$sampleSize.width} collection_id={collectionId} />
