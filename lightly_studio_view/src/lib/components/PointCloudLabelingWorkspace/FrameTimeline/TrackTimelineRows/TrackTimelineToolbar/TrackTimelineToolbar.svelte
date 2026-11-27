<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { MultiSelectPopover } from '$lib/components/MultiSelectPopover';
    import TrackAnnotationLegend from '../TrackAnnotationLegend/TrackAnnotationLegend.svelte';

    type RowsVisibility = Pick<
        ComponentProps<typeof MultiSelectPopover>,
        'items' | 'selectedIds' | 'onChange'
    > & { visibleCount: number };
    // The pickers sit in the compact timeline toolbar.
    const ROW_PICKER_TRIGGER_CLASS = 'h-6 gap-1 px-2';

    /**
     * Actions of the object tracks panel: add or start a track, pick the visible tracks, and the
     * legend.
     */
    interface Props {
        trackVisibility: RowsVisibility | null;
        onAddTrack?: () => void;
        isAddingTrack: boolean;
        onStartTrack?: () => void;
    }

    const { trackVisibility, onAddTrack, isAddingTrack, onStartTrack }: Props = $props();
</script>

<div class="flex items-center gap-2" data-testid="track-timeline-toolbar">
    {#if onAddTrack}
        <Button
            variant={isAddingTrack ? 'default' : 'outline'}
            size="sm"
            class="h-6 text-xs"
            onclick={onAddTrack}
        >
            {isAddingTrack ? 'Cancel' : 'Add object track'}
        </Button>
        {#if isAddingTrack}
            <span class="text-xs text-muted-foreground">
                Click in the 3D scene to place the first cuboid.
            </span>
        {/if}
    {/if}
    {#if onStartTrack}
        <Button variant="outline" size="sm" class="h-6 text-xs" onclick={onStartTrack}>
            Start track from selected cuboid
        </Button>
    {/if}
    {#if trackVisibility}
        <MultiSelectPopover
            items={trackVisibility.items}
            selectedIds={trackVisibility.selectedIds}
            onChange={trackVisibility.onChange}
            label={`Showing ${trackVisibility.visibleCount} of ${trackVisibility.items.length} tracks`}
            itemNoun="track"
            itemNounPlural="tracks"
            showSelectAll
            triggerClass={ROW_PICKER_TRIGGER_CLASS}
            testId="track-visibility-select"
        />
        <TrackAnnotationLegend />
    {/if}
</div>
