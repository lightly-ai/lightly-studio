<script lang="ts">
    import { Diamond, Plus, Trash2 } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn.js';
    import { toContiguousRuns } from './contiguousRuns';
    import type { TimelineTrack } from '../types';

    /**
     * One object track's lane: a label button that reports selection, a strip showing every
     * contiguous run of frames the track has geometry for (authored or interpolated), a diamond
     * per authored keyframe, and an add/remove affordance for keyframes at the active frame.
     *
     * Frame positions the track has no geometry for are simply not covered by a run, which is
     * what makes an empty gap or a sparse track visible: unlike `VideoEventTimeline`, a lane here
     * is drawn from discrete frame positions, not a continuous time span.
     */
    interface Props {
        track: TimelineTrack;
        /** Frames discovered so far; positions are placed relative to this range. */
        frameCount: number;
        /** Current frame position, if known, for the add-keyframe affordance. */
        activeFramePosition?: number;
        selected?: boolean;
        onSelect?: (trackId: string) => void;
        onAddKeyframe?: (trackId: string, framePosition: number) => void;
        onRemoveKeyframe?: (trackId: string, keyframeId: string) => void;
    }

    let {
        track,
        frameCount,
        activeFramePosition,
        selected = false,
        onSelect,
        onAddKeyframe,
        onRemoveKeyframe
    }: Props = $props();

    const lastPosition = $derived(Math.max(0, frameCount - 1));
    const toPercent = (position: number) => (frameCount > 1 ? (position / lastPosition) * 100 : 0);
    const runs = $derived(toContiguousRuns(track.presentFramePositions));
    const laneColor = $derived(track.color ?? 'hsl(var(--muted-foreground))');

    const hasKeyframeAtActivePosition = $derived(
        activeFramePosition !== undefined &&
            track.keyframes.some((keyframe) => keyframe.framePosition === activeFramePosition)
    );
    const canAddKeyframeHere = $derived(
        !!onAddKeyframe && activeFramePosition !== undefined && !hasKeyframeAtActivePosition
    );
</script>

<div
    class={cn('flex items-center gap-2 rounded px-1 py-0.5', selected && 'bg-accent')}
    data-testid="workspace-timeline-track"
>
    <button
        type="button"
        class="flex w-20 shrink-0 items-center gap-1.5 truncate text-left text-xs text-muted-foreground hover:text-foreground"
        aria-pressed={selected}
        onclick={() => onSelect?.(track.id)}
    >
        <span
            class="size-1.5 shrink-0 rounded-full"
            style={`background-color: ${laneColor};`}
            aria-hidden="true"
        ></span>
        <span class="truncate">{track.label}</span>
    </button>
    <div class="relative h-4 flex-1 rounded bg-muted/50">
        {#each runs as run (run.start)}
            <div
                class="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full"
                style={`left: ${toPercent(run.start)}%; width: ${Math.max(1, toPercent(run.end) - toPercent(run.start))}%; background-color: ${laneColor};`}
            ></div>
        {/each}
        {#each track.keyframes as keyframe (keyframe.id)}
            <div
                class="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
                style={`left: ${toPercent(keyframe.framePosition)}%;`}
            >
                <Diamond
                    class="size-2.5 fill-current"
                    style={`color: ${laneColor};`}
                    aria-hidden="true"
                />
                {#if onRemoveKeyframe}
                    <button
                        type="button"
                        class="absolute -top-4 left-1/2 hidden -translate-x-1/2 rounded bg-black/70 p-0.5 text-white group-hover:block"
                        aria-label={`Remove keyframe on frame ${keyframe.framePosition + 1} of ${track.label}`}
                        onclick={(event) => {
                            event.stopPropagation();
                            onRemoveKeyframe?.(track.id, keyframe.id);
                        }}
                    >
                        <Trash2 class="size-2.5" />
                    </button>
                {/if}
            </div>
        {/each}
    </div>
    {#if onAddKeyframe}
        <button
            type="button"
            class="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground disabled:opacity-30"
            disabled={!canAddKeyframeHere}
            aria-label={`Add keyframe on the current frame for ${track.label}`}
            onclick={() =>
                activeFramePosition !== undefined && onAddKeyframe?.(track.id, activeFramePosition)}
        >
            <Plus class="size-3" aria-hidden="true" />
        </button>
    {/if}
</div>
