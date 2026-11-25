<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { MultiSelectPopover } from '$lib/components/MultiSelectPopover';
    import TrackAnnotationLegend from '../TrackAnnotationLegend/TrackAnnotationLegend.svelte';

    type RowsVisibility = Pick<
        ComponentProps<typeof MultiSelectPopover>,
        'items' | 'selectedIds' | 'onChange'
    > & { visibleCount: number };
    // The pickers sit in the compact timeline toolbar.
    const ROW_PICKER_TRIGGER_CLASS = 'h-6 gap-1 px-2';

    /**
     * Actions above the track rows: add or start a track, pick visible tracks, the legend, the
     * frame tags toggle, and pick visible frame tags.
     */
    interface Props {
        trackVisibility: RowsVisibility | null;
        onAddTrack?: () => void;
        isAddingTrack: boolean;
        onStartTrack?: () => void;
        /** Set when frame tags can be shown on the timeline. */
        frameTags?: { checked: boolean; onCheckedChange: (checked: boolean) => void };
        /** Set while frame tag rows are shown. */
        tagVisibility?: RowsVisibility;
    }

    const {
        trackVisibility,
        onAddTrack,
        isAddingTrack,
        onStartTrack,
        frameTags,
        tagVisibility
    }: Props = $props();
</script>

<!--
    The actions stick to the left edge and the legend and frame tag controls to the right edge, so
    both stay in view while the zoomed timeline scrolls.
-->
<div class="flex items-center justify-between gap-2" data-testid="track-timeline-toolbar">
    <div class="sticky left-2 flex items-center gap-2">
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
        {/if}
    </div>
    <div class="sticky right-2 flex items-center gap-4">
        {#if trackVisibility}
            <TrackAnnotationLegend />
        {/if}
        {#if frameTags}
            <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Checkbox checked={frameTags.checked} onCheckedChange={frameTags.onCheckedChange} />
                Show frame tags
            </label>
        {/if}
        {#if tagVisibility}
            <MultiSelectPopover
                items={tagVisibility.items}
                selectedIds={tagVisibility.selectedIds}
                onChange={tagVisibility.onChange}
                label={`Showing ${tagVisibility.visibleCount} of ${tagVisibility.items.length} tags`}
                itemNoun="tag"
                itemNounPlural="tags"
                showSelectAll
                triggerClass={ROW_PICKER_TRIGGER_CLASS}
                testId="tag-visibility-select"
            />
        {/if}
    </div>
</div>
