<script lang="ts">
    import { ChevronLeft, ChevronRight, Pause, Play } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import FrameTimelineRuler from './FrameTimelineRuler.svelte';
    import TrackLane from './TrackLane.svelte';
    import { useFramePlayback } from './useFramePlayback.svelte';
    import type { FrameNavigation, TimelineTrack } from '../types';

    /**
     * Frame navigation, object tracks and keyframes for the active recording.
     *
     * Stepping, scrubbing (drag/click/arrow-key the ruler, when `navigation.seek` is given) and
     * playback move `navigation`. Tracks are drawn from already-adapted `TimelineTrack`s (see
     * `toTimelineTracks`), so this component never touches domain or transport types directly.
     */
    interface Props {
        navigation?: FrameNavigation;
        tracks?: readonly TimelineTrack[];
        /** Track whose lane is highlighted, e.g. the scene's primary selection. */
        selectedTrackId?: string;
        onSelectTrack?: (trackId: string) => void;
        onAddKeyframe?: (trackId: string, framePosition: number) => void;
        onRemoveKeyframe?: (trackId: string, keyframeId: string) => void;
        /**
         * Consulted before a user-initiated step, scrub, or the start of playback. Returning
         * false (or resolving to false) cancels the move, e.g. to offer a save/discard prompt for
         * unsaved edits. Absent means navigation is never blocked. Once playback has started,
         * later automatic steps are not re-guarded.
         */
        guardNavigation?: () => boolean | Promise<boolean>;
    }

    let {
        navigation,
        tracks = [],
        selectedTrackId,
        onSelectTrack,
        onAddKeyframe,
        onRemoveKeyframe,
        guardNavigation
    }: Props = $props();

    const playback = useFramePlayback(() => navigation);

    const label = $derived(
        navigation
            ? `Frame ${navigation.position + 1} / ${navigation.frameCount}${navigation.hasMore ? '+' : ''}`
            : 'Frame — / —'
    );

    async function guarded(action: () => void) {
        if (guardNavigation && !(await guardNavigation())) return;
        action();
    }
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-frame-timeline"
>
    <div class="flex shrink-0 items-center gap-1 border-b px-2 py-1">
        <Button
            variant="ghost"
            icon={ChevronLeft}
            ariaLabel="Previous frame"
            buttonProps={{
                disabled: !navigation || navigation.position === 0,
                onclick: () => guarded(() => navigation?.previous()),
                size: 'sm',
                class: 'h-7 w-7 p-0'
            }}
        />
        <Button
            variant="ghost"
            icon={playback.isPlaying ? Pause : Play}
            ariaLabel={playback.isPlaying ? 'Pause playback' : 'Play frames'}
            buttonProps={{
                disabled: !navigation || (!playback.isPlaying && playback.isAtLastFrame),
                onclick: () => playback.toggle(guardNavigation),
                size: 'sm',
                class: 'h-7 w-7 p-0'
            }}
        />
        <Button
            variant="ghost"
            icon={ChevronRight}
            ariaLabel="Next frame"
            buttonProps={{
                disabled: !navigation || playback.isAtLastFrame,
                onclick: () => guarded(() => navigation?.next()),
                size: 'sm',
                class: 'h-7 w-7 p-0'
            }}
        />
        <span class="ml-2 text-xs text-muted-foreground" data-testid="workspace-frame-position">
            {label}
        </span>
        {#if navigation?.isLoading}
            <span class="text-xs text-muted-foreground">loading…</span>
        {/if}
    </div>
    <div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-2 py-1.5">
        <FrameTimelineRuler
            frameCount={navigation?.frameCount ?? 0}
            position={navigation?.position ?? 0}
            disabled={!navigation?.seek}
            onScrub={navigation?.seek
                ? (position) => guarded(() => navigation?.seek?.(position))
                : undefined}
        />
        {#if tracks.length === 0}
            <p class="px-1 py-2 text-xs text-muted-foreground">
                No object tracks for this frame range.
            </p>
        {:else}
            {#each tracks as track (track.id)}
                <TrackLane
                    {track}
                    frameCount={navigation?.frameCount ?? 0}
                    activeFramePosition={navigation?.position}
                    selected={track.id === selectedTrackId}
                    onSelect={onSelectTrack}
                    {onAddKeyframe}
                    {onRemoveKeyframe}
                />
            {/each}
        {/if}
    </div>
</div>
