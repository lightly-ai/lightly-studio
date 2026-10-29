<script lang="ts">
    import { Images } from '$lib/components/index.js';
    import { page } from '$app/state';

    const { data } = $props();

    const sampleSize = $derived(data.sampleSize);
    const textEmbedding = $derived(data.globalStorage.textEmbedding);

    const collection_id = $derived(page.params.collection_id!);
</script>

<Images sampleWidth={$sampleSize.width} {textEmbedding} {collection_id} />
