<script lang="ts">
    import { Button } from '$lib/components/Button';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { FilterX } from '@lucide/svelte';
    import { toStore } from 'svelte/store';
    import { useClearAllFilters } from './useClearAllFilters';

    interface Props {
        collectionId: string;
        isCaptions?: boolean;
        isImages: boolean;
        isVideos: boolean;
        isVideoFrames: boolean;
        treeCollectionId?: string;
        treeFilterActive?: boolean;
    }

    let {
        collectionId,
        isCaptions = false,
        isImages,
        isVideos,
        isVideoFrames,
        treeCollectionId,
        treeFilterActive = false
    }: Props = $props();

    const { hasActiveFilters, clearAllFilters } = $derived(
        useClearAllFilters({
            collectionId,
            isCaptions,
            isImages,
            isVideos,
            isVideoFrames,
            treeCollectionId,
            treeFilterActive: toStore(() => treeFilterActive)
        })
    );
</script>

{#if $hasActiveFilters}
    <Tooltip content="Clear all filters" position="bottom" class="w-max">
        <Button
            variant="ghost"
            icon={FilterX}
            ariaLabel="Clear all filters"
            buttonProps={{
                onclick: clearAllFilters,
                'data-testid': 'clear-all-filters',
                class: 'size-6 p-0'
            }}
        />
    </Tooltip>
{/if}
