<script lang="ts">
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
</script>

Groups pages: {data.collection.collection_id}
