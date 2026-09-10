<script lang="ts">
    import { ChevronLeft, ChevronRight, Play } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { FrameNavigation } from '../types';

    /**
     * Frame navigation, object tracks and keyframes for the active recording.
     *
     * Stepping is wired when a `navigation` is given; the ruler and lanes are still
     * placeholders, and playback stays disabled until it exists.
     */
    interface Props {
        navigation?: FrameNavigation;
    }

    let { navigation }: Props = $props();

    const ticks = Array.from({ length: 24 }, (_, index) => index);
    const lanes = ['Track 1', 'Track 2'];

    // More frames are listed on demand, so the end is only reached when nothing is known
    // ahead and the channel has nothing left either.
    const isAtLastFrame = $derived(
        !!navigation && !navigation.hasMore && navigation.position >= navigation.frameCount - 1
    );

    const label = $derived(
        navigation
            ? `Frame ${navigation.position + 1} / ${navigation.frameCount}${navigation.hasMore ? '+' : ''}`
            : 'Frame — / —'
    );
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
                onclick: () => navigation?.previous(),
                size: 'sm',
                class: 'h-7 w-7 p-0'
            }}
        />
        <Button
            variant="ghost"
            icon={Play}
            ariaLabel="Play frames"
            buttonProps={{ disabled: true, size: 'sm', class: 'h-7 w-7 p-0' }}
        />
        <Button
            variant="ghost"
            icon={ChevronRight}
            ariaLabel="Next frame"
            buttonProps={{
                disabled: !navigation || isAtLastFrame,
                onclick: () => navigation?.next(),
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
        <div class="flex h-4 shrink-0 items-end gap-px" aria-hidden="true">
            {#each ticks as tick (tick)}
                <span class="w-full bg-border {tick % 5 === 0 ? 'h-3' : 'h-1.5'}"></span>
            {/each}
        </div>
        {#each lanes as lane (lane)}
            <div class="flex items-center gap-2">
                <span class="w-14 shrink-0 truncate text-xs text-muted-foreground">{lane}</span>
                <div class="h-4 flex-1 rounded bg-muted/50"></div>
            </div>
        {/each}
    </div>
</div>
