<script lang="ts">
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';

    const { collectionId }: { collectionId: string } = $props();

    const { modelOverlays, addModelOverlay, removeModelOverlay } = useGlobalStorage();

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
        <div class="width-full space-y-2 overflow-hidden">
            {#each collections as col (col.collection_id)}
                {@const overlay = getOverlay(col.collection_id)}
                {@const isActive = !!overlay}
                <div class="width-full flex items-center space-x-2" title={col.name}>
                    <Checkbox
                        id={col.collection_id}
                        checked={isActive}
                        onCheckedChange={() => toggleCollection(col.collection_id)}
                    />
                    <Label
                        for={col.collection_id}
                        class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                        <span
                            class="h-3 w-3 shrink-0 rounded-sm {isActive
                                ? 'opacity-100'
                                : 'opacity-40'}"
                            style="background-color: {overlay?.color ?? '#6B7280'};"
                        ></span>
                        <p class="flex-1 truncate text-base font-normal">
                            {col.name}
                        </p>
                    </Label>
                </div>
            {/each}
        </div>
    {/if}
</Segment>
