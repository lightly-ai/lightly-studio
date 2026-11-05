<script lang="ts">
    import {
        MAX_TRACK_ROWS_HEIGHT,
        MIN_TRACK_ROWS_HEIGHT,
        type useTrackRowsHeight
    } from './useTrackRowsHeight.svelte';

    /** A handle above the track rows: drag up for taller rows, down for shorter ones. */
    interface Props {
        rowsHeight: ReturnType<typeof useTrackRowsHeight>;
    }

    const { rowsHeight }: Props = $props();
    const KEYBOARD_STEP = 24;

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'ArrowUp') rowsHeight.setHeight(rowsHeight.height + KEYBOARD_STEP);
        else if (event.key === 'ArrowDown') rowsHeight.setHeight(rowsHeight.height - KEYBOARD_STEP);
        else return;
        event.preventDefault();
    }
</script>

<div
    role="slider"
    aria-orientation="vertical"
    aria-label="Resize track timeline"
    aria-valuenow={rowsHeight.height}
    aria-valuemin={MIN_TRACK_ROWS_HEIGHT}
    aria-valuemax={MAX_TRACK_ROWS_HEIGHT}
    tabindex="0"
    class="group flex h-2 cursor-row-resize touch-none items-center justify-center bg-card"
    data-testid="track-rows-resizer"
    onpointerdown={rowsHeight.startDrag}
    onpointermove={rowsHeight.drag}
    onpointerup={rowsHeight.endDrag}
    onpointercancel={rowsHeight.endDrag}
    onkeydown={handleKeydown}
>
    <div class="flex gap-0.5 opacity-40 transition-opacity group-hover:opacity-100">
        <span class="size-1 rounded-full bg-muted-foreground"></span>
        <span class="size-1 rounded-full bg-muted-foreground"></span>
        <span class="size-1 rounded-full bg-muted-foreground"></span>
    </div>
</div>
