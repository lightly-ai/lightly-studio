<script lang="ts">
    import type { Snippet } from 'svelte';

    const {
        children,
        fullWidth = false,
        onscroll
    }: { children: Snippet; fullWidth?: boolean; onscroll?: (e: Event) => void } = $props();

    function handleScroll(e: Event) {
        if (onscroll) {
            onscroll(e);
        }
    }
</script>

<header>
    <div class="p mb-3 border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground">
        <div class="flex justify-between">
            <div class="flex w-[320px]">
                <a href="/"><Logo /></a>
            </div>
            <div class="flex flex-1 justify-start">
                {#if $datasetCollection.data && !Array.isArray($datasetCollection.data)}
                    <NavigationMenu collection={$datasetCollection.data} />
                {/if}
            </div>
            <div class="flex flex-auto justify-end gap-2"></div>
        </div>
    </div>
</header>
