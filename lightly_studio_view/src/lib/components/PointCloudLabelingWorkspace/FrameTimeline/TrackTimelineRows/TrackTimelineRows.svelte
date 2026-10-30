<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { buildTrackTimeline } from './buildTrackTimeline';

    interface Props {
        ticks: TickView[];
        tracks: SequenceTrackView[];
        currentTick: number;
        onSelectTick: (seqNumber: number) => void;
    }

    let { ticks, tracks, currentTick, onSelectTick }: Props = $props();
    let selectedTrackId = $state<string | null>(null);
    const selectedTrack = $derived(
        tracks.find((track) => track.object_track_id === selectedTrackId) ?? tracks[0]
    );
    const currentIndex = $derived(ticks.findIndex((tick) => tick.seq_number === currentTick));
    const keyframes = $derived(
        selectedTrack
            ? buildTrackTimeline(selectedTrack, ticks).annotations.filter(
                  (item) => !item.interpolated
              )
            : []
    );

    function seekKeyframe(direction: -1 | 1) {
        const candidates = keyframes.filter((item) =>
            direction < 0 ? item.index! < currentIndex : item.index! > currentIndex
        );
        const target = direction < 0 ? candidates.at(-1) : candidates[0];
        if (target) onSelectTick(target.seq_number);
    }
</script>

{#if tracks.length > 0 && ticks.length > 0}
    <div class="border-t text-xs" data-testid="track-timeline">
        <div class="flex items-center justify-between px-2 py-1">
            <span class="font-medium">Object tracks</span>
            <div class="flex gap-2">
                <button
                    type="button"
                    aria-label="Previous keyframe"
                    disabled={!keyframes.some((item) => item.index! < currentIndex)}
                    onclick={() => seekKeyframe(-1)}>Previous</button
                >
                <button
                    type="button"
                    aria-label="Next keyframe"
                    disabled={!keyframes.some((item) => item.index! > currentIndex)}
                    onclick={() => seekKeyframe(1)}>Next</button
                >
            </div>
        </div>
        <div class="max-h-32 overflow-y-auto">
            {#each tracks as track (track.object_track_id)}
                {@const timeline = buildTrackTimeline(track, ticks)}
                <div class="flex h-6 items-center border-t border-border/50">
                    <button
                        type="button"
                        class="w-20 shrink-0 truncate px-2 text-left hover:text-primary"
                        aria-pressed={selectedTrack?.object_track_id === track.object_track_id}
                        onclick={() => {
                            selectedTrackId = track.object_track_id;
                            if (timeline.annotations[0])
                                onSelectTick(timeline.annotations[0].seq_number);
                        }}>Track {track.object_track_number}</button
                    >
                    <div class="relative mx-2 h-4 min-w-0 flex-1">
                        {#each timeline.runs as run}
                            <span
                                class="absolute top-1 h-2 rounded-sm {run.interpolated
                                    ? 'bg-primary/35'
                                    : 'bg-primary/70'}"
                                style:left={`${(run.startIndex / ticks.length) * 100}%`}
                                style:width={`${((run.endIndex - run.startIndex + 1) / ticks.length) * 100}%`}
                                title={run.interpolated
                                    ? 'Generated annotations'
                                    : 'Authored annotations'}
                            ></span>
                        {/each}
                        {#each timeline.annotations.filter((item) => !item.interpolated) as item (item.annotation_id)}
                            <button
                                type="button"
                                class="absolute top-0 z-10 h-4 w-1.5 -translate-x-1/2 rounded-sm bg-primary ring-1 ring-background"
                                style:left={`${((item.index! + 0.5) / ticks.length) * 100}%`}
                                aria-label={`Track ${track.object_track_number} keyframe at frame ${item.index! + 1}`}
                                onclick={() => {
                                    selectedTrackId = track.object_track_id;
                                    onSelectTick(item.seq_number);
                                }}
                            ></button>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    </div>
{/if}
