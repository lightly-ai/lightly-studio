<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import TrackAnnotationLegend from '../TrackAnnotationLegend/TrackAnnotationLegend.svelte';
    import { TrackVisibilitySelect } from '../TrackVisibilitySelect';

    /**
     * Actions above the track rows: add or start a track, pick visible tracks, the legend, and
     * the frame tags toggle.
     */
    interface Props {
        visibility: ComponentProps<typeof TrackVisibilitySelect> | null;
        onAddTrack?: () => void;
        isAddingTrack: boolean;
        onStartTrack?: () => void;
        /** Set when frame tags can be shown on the timeline. */
        frameTags?: { checked: boolean; onCheckedChange: (checked: boolean) => void };
    }

    const { visibility, onAddTrack, isAddingTrack, onStartTrack, frameTags }: Props = $props();
</script>

<div class="mb-1 flex items-center gap-2">
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
    {#if visibility}
        <TrackVisibilitySelect {...visibility} />
        <TrackAnnotationLegend />
    {/if}
    {#if frameTags}
        <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Checkbox checked={frameTags.checked} onCheckedChange={frameTags.onCheckedChange} />
            Show frame tags
        </label>
    {/if}
</div>
