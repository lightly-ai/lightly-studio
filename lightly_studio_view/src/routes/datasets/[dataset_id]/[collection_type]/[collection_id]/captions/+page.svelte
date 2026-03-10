<script lang="ts">
    import { page } from '$app/state';
    import Captions from '$lib/components/Captions/Captions.svelte';

    const collectionId = $derived(page.params.collection_id);
</script>

{#key collectionId}
    <Captions {collectionId} />
{/key}
