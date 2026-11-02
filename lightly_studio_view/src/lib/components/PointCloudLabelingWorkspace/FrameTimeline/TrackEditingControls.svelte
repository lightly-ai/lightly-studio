<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import type { CuboidAnnotation } from '../domain';
    import { useTrackEditing } from './useTrackEditing.svelte';

    interface Props {
        datasetId: string;
        sequenceId: string;
        currentTick: number;
        ticks: TickView[];
        selectedCuboid?: CuboidAnnotation;
        selectedTrack?: SequenceTrackView;
        onTrackStarted: (id: string) => void;
        onSaved: () => Promise<unknown>;
    }

    let {
        datasetId,
        sequenceId,
        currentTick,
        ticks,
        selectedCuboid,
        selectedTrack,
        onTrackStarted,
        onSaved
    }: Props = $props();
    let mode = $state<'hold' | 'interpolate'>('interpolate');
    const editing = useTrackEditing(
        () => ({ datasetId, sequenceId }),
        () => onSaved()
    );
    const lastKeyframe = $derived(
        selectedTrack?.annotations.filter((annotation) => !annotation.interpolated).at(-1)
    );
    const intermediateCount = $derived(
        lastKeyframe
            ? ticks.filter(
                  (tick) =>
                      tick.seq_number > lastKeyframe.seq_number && tick.seq_number < currentTick
              ).length
            : 0
    );
    async function start() {
        if (!selectedCuboid) return;
        const trackId = await editing.start(selectedCuboid.id);
        if (trackId) onTrackStarted(trackId);
    }

    async function extend() {
        if (!selectedCuboid || !selectedTrack?.managed || !lastKeyframe) return;
        if (
            intermediateCount > 0 &&
            !window.confirm(
                `Generate ${intermediateCount} cuboid${intermediateCount === 1 ? '' : 's'} between the keyframes using ${mode} mode?`
            )
        )
            return;
        await editing.extend(selectedTrack.object_track_id, selectedCuboid.id, mode);
    }
</script>

<div
    class="flex min-h-9 items-center gap-2 border-t px-2 py-1 text-xs"
    data-testid="track-editing-controls"
>
    <span class="font-medium">Track editing</span>
    {#if selectedCuboid && !selectedCuboid.trackId}
        <button
            type="button"
            class="rounded border px-2 py-1 hover:bg-accent"
            disabled={editing.saving}
            onclick={start}
        >
            Start track
        </button>
        {#if selectedTrack?.managed}
            <label for="track-interval-mode">Fill</label>
            <select
                id="track-interval-mode"
                class="rounded border bg-background px-1 py-1"
                bind:value={mode}
            >
                <option value="interpolate">Interpolate</option>
                <option value="hold">Hold</option>
            </select>
            <button
                type="button"
                class="rounded border px-2 py-1 hover:bg-accent"
                disabled={editing.saving || !lastKeyframe || currentTick <= lastKeyframe.seq_number}
                onclick={extend}
            >
                Add keyframe to track {selectedTrack.object_track_number}
            </button>
        {/if}
    {:else if selectedCuboid?.trackId}
        <span>Selected cuboid belongs to track {selectedCuboid.trackNumber ?? ''}.</span>
    {:else}
        <span class="text-muted-foreground"
            >Select a cuboid to start a track or add a keyframe.</span
        >
    {/if}
</div>
