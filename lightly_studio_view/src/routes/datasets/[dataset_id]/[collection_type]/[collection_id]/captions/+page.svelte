<script lang="ts">
    import Captions from '$lib/components/Captions/Captions.svelte';

    const { data } = $props();
    const collectionId = data.collection?.collection_id ?? '';
</script>

<Captions {collectionId} />
