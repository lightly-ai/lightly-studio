<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { TrackSelect } from '$lib/components/TrackSelect';
    import { Typography } from '$lib/components/Typography';
    import { useAnnotationTrackEditing } from './useAnnotationTrackEditing.svelte';

    interface Props {
        annotationId: string;
        annotationSourceId: string;
        trackId: string | null;
        annotationClassName: string | null;
        trackNumber: number | null;
        parentTrackNumber: number | null;
        parentTrackClassName: string | null;
        editable: boolean;
        occupiedTrackIds: ReadonlySet<string>;
        onTrackChange?: () => Promise<void>;
    }

    let {
        annotationId,
        annotationSourceId,
        trackId,
        annotationClassName,
        trackNumber,
        parentTrackNumber,
        parentTrackClassName,
        editable,
        occupiedTrackIds,
        onTrackChange
    }: Props = $props();
    const editing = useAnnotationTrackEditing({
        getAnnotation: () => ({
            id: annotationId,
            annotationSourceId,
            trackId,
            annotationClassName
        }),
        getOccupiedTrackIds: () => occupiedTrackIds,
        onTrackChange: async () => {
            await onTrackChange?.();
        }
    });
    const { disabled, isSaving, needsRefresh, error, retryRefresh } = editing.state;
</script>

{#if editable}
    <div class="flex flex-col gap-y-1">
        <Typography component="dt" variant="body2">Track:</Typography>
        <dd class="min-w-0">
            <TrackSelect
                tracks={editing.availableTracks}
                value={trackId ?? '__no_track__'}
                disabled={$disabled || editing.isPending}
                isLoading={$isSaving || editing.isPending}
                className="w-full"
                onValueChange={editing.handleTrackChange}
            />
        </dd>
    </div>
{:else if trackNumber !== null}
    <div class="grid grid-cols-[5rem_1fr] gap-x-2">
        <Typography component="dt" variant="body2">Track number:</Typography>
        <Typography component="dd" variant="body2">{trackNumber}</Typography>
    </div>
{/if}

{#if editable && trackId}
    <div class="flex flex-col gap-y-1">
        <Typography component="dt" variant="body2">Parent track:</Typography>
        <dd class="min-w-0">
            <TrackSelect
                tracks={editing.parentTrackTracks}
                value={editing.currentTrack?.parent_object_track_id ?? '__no_track__'}
                noSelectionLabel="No parent"
                showNewTrack={false}
                disabled={$disabled || editing.isPending || editing.isTracksNotReady}
                isLoading={$isSaving || editing.isPending || editing.isTracksNotReady}
                className="w-full"
                onValueChange={(id) => editing.handleParentTrackChange(id)}
            />
        </dd>
    </div>
{:else if parentTrackNumber !== null}
    <div class="grid grid-cols-[5rem_1fr] gap-x-2">
        <Typography component="dt" variant="body2">Parent track:</Typography>
        <Typography component="dd" variant="body2">
            {#if parentTrackClassName}
                {parentTrackClassName} - {parentTrackNumber}
            {:else}
                Track {parentTrackNumber}
            {/if}
        </Typography>
    </div>
{/if}

{#if editable && $error}
    <div role="alert">
        <Typography component="p" variant="body2">{$error}</Typography>
        {#if $needsRefresh}
            <Button variant="secondary" disabled={$isSaving} onclick={retryRefresh}
                >Retry refresh</Button
            >
        {/if}
    </div>
{/if}
