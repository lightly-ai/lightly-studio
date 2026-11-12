<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import TrackAnnotationLegend from '../TrackAnnotationLegend/TrackAnnotationLegend.svelte';
    import { TrackVisibilitySelect } from '../TrackVisibilitySelect';

    /** Actions above the track rows: add or start a track, pick visible tracks, and the legend. */
    interface Props {
        visibility: ComponentProps<typeof TrackVisibilitySelect> | null;
        onAddTrack?: () => void;
        isAddingTrack: boolean;
        onStartTrack?: () => void;
    }

    const { visibility, onAddTrack, isAddingTrack, onStartTrack }: Props = $props();
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
</div>
