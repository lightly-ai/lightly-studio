<script lang="ts">
    import { Images } from '$lib/components/index.js';
    import { page } from '$app/state';
    import { useOpenSample } from '$lib/hooks/useOpenSample/useOpenSample';

    const { data } = $props();

    const sampleSize = $derived(data.sampleSize);
    const textEmbedding = $derived(data.globalStorage.textEmbedding);

    const collection_id = $derived(page.params.collection_id!);

    // Back on the grid means the details view was closed, so the tab opens on the grid again.
    const { forgetOpenSample } = useOpenSample();
    $effect(() => forgetOpenSample(collection_id));
</script>

<Images sampleWidth={$sampleSize.width} {textEmbedding} {collection_id} />
