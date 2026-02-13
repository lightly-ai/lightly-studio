<script lang="ts">
    import Layout from '$lib/components/Layout/Layout.svelte';
    import LayoutSection from '$lib/components/LayoutSection/LayoutSection.svelte';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
</script>

Groups pages: {data.collection.collection_id}
