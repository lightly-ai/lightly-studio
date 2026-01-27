<script lang="ts">
    import { page } from '$app/state';
    import Captions from '$lib/components/Captions/Captions.svelte';

    const collectionId = page.params.collection_id;
</script>

<Captions {collectionId} />
