<script lang="ts">
    import { Button } from '$lib/components/Button';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { FilterX } from '@lucide/svelte';
    import { useClearAllFilters } from './useClearAllFilters';

    interface Props {
        collectionId: string;
        isImages: boolean;
        isVideos: boolean;
        isVideoFrames: boolean;
    }

    let { collectionId, isImages, isVideos, isVideoFrames }: Props = $props();

    const { hasActiveFilters, clearAllFilters } = $derived(
        useClearAllFilters({ collectionId, isImages, isVideos, isVideoFrames })
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
