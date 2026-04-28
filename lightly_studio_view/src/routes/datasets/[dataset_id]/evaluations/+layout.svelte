<script lang="ts">
    import { page } from '$app/state';
    import { Header } from '$lib/components';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import type { Snippet } from 'svelte';

    const { children }: { children: Snippet } = $props();
    const { collection } = $derived.by(() =>
        useCollection({ collectionId: page.params.dataset_id! })
    );
</script>

{#if $collection.data}
    <Header collection={$collection.data} />
{/if}

<main class="flex-1 bg-background px-6 py-6">
    {@render children()}
</main>
