<script lang="ts">
    /**
     * Frame ruler: tick marks across the known frame range, a playhead at the current position,
     * and click/drag/arrow-key scrubbing when `onScrub` is given.
     */
    interface Props {
        /** Frames discovered so far; the ruler only ever addresses positions within this. */
        frameCount: number;
        /** Zero-based current position. */
        position: number;
        /** True when scrubbing is unavailable, e.g. `FrameNavigation.seek` was not given. */
        disabled?: boolean;
        onScrub?: (position: number) => void;
    }

    let { frameCount, position, disabled = false, onScrub }: Props = $props();

    let trackEl = $state<HTMLDivElement | undefined>(undefined);
    let dragging = $state(false);

    const lastPosition = $derived(Math.max(0, frameCount - 1));
    const toPercent = (pos: number) => (frameCount > 1 ? (pos / lastPosition) * 100 : 0);

    function positionFromClientX(clientX: number): number {
        if (!trackEl || frameCount <= 1) return 0;
        const rect = trackEl.getBoundingClientRect();
        const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
        return Math.round(Math.min(1, Math.max(0, ratio)) * lastPosition);
    }

    function scrubToClientX(clientX: number) {
        if (disabled || !onScrub) return;
        onScrub(positionFromClientX(clientX));
    }

    function handleKeydown(event: KeyboardEvent) {
        if (disabled || !onScrub) return;
        if (event.key === 'ArrowRight') onScrub(Math.min(lastPosition, position + 1));
        else if (event.key === 'ArrowLeft') onScrub(Math.max(0, position - 1));
    }
</script>

<div
    bind:this={trackEl}
    class="relative h-4 shrink-0 {disabled ? '' : 'cursor-pointer'}"
    role="slider"
    tabindex={disabled ? -1 : 0}
    aria-label="Scrub frames"
    aria-valuemin={0}
    aria-valuemax={lastPosition}
    aria-valuenow={position}
    aria-disabled={disabled}
    data-testid="workspace-frame-ruler"
    onpointerdown={(event) => {
        if (disabled) return;
        dragging = true;
        (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
        scrubToClientX(event.clientX);
    }}
    onpointermove={(event) => dragging && scrubToClientX(event.clientX)}
    onpointerup={() => (dragging = false)}
    onkeydown={handleKeydown}
>
    <div class="absolute inset-0 flex items-end gap-px" aria-hidden="true">
        {#each Array.from({ length: frameCount }, (_, index) => index) as tick (tick)}
            <span class="w-full bg-border {tick % 5 === 0 ? 'h-3' : 'h-1.5'}"></span>
        {/each}
    </div>
    {#if frameCount > 0}
        <div
            class="pointer-events-none absolute top-0 z-10 h-full w-0.5 -translate-x-1/2 bg-primary"
            style={`left: ${toPercent(position)}%;`}
            aria-hidden="true"
        ></div>
    {/if}
</div>
