<script lang="ts">
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Segment from '$lib/components/Segment/Segment.svelte';

    const { collectionId }: { collectionId: string } = $props();

    const { modelOverlays, addModelOverlay, removeModelOverlay, updateModelOverlay } =
        useGlobalStorage();

    const collectionsQuery = $derived(useAnnotationCollections({ collectionId }));
    const collections = $derived($collectionsQuery.data ?? []);

    function toggleCollection(id: string) {
        const exists = $modelOverlays.some((o) => o.collectionId === id);
        if (exists) {
            removeModelOverlay(id);
        } else {
            addModelOverlay(id);
        }
    }

    function getOverlay(id: string) {
        return $modelOverlays.find((o) => o.collectionId === id);
    }
</script>

<Segment title="Collections">
    {#if collections.length === 0}
        <div class="py-2 text-xs text-muted-foreground">No annotation collections</div>
    {:else}
        <div class="space-y-3">
            {#each collections as col (col.collection_id)}
                {@const overlay = getOverlay(col.collection_id)}
                {@const isActive = !!overlay}
                <div class="space-y-1.5">
                    <div class="flex items-center gap-2">
                        <button
                            class="h-4 w-4 shrink-0 rounded border border-border transition-opacity {isActive
                                ? 'opacity-100'
                                : 'opacity-30'}"
                            style="background-color: {overlay?.color ?? '#6B7280'};"
                            onclick={() => toggleCollection(col.collection_id)}
                            title={isActive ? 'Hide' : 'Show'}
                        ></button>
                        <span
                            class="truncate text-sm {isActive ? '' : 'text-muted-foreground'}"
                            title={col.name}
                        >
                            {col.name}
                        </span>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</Segment>
