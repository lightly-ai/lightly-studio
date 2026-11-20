<script lang="ts">
    import type {
        SequenceTrackView,
        TickTagView,
        TickView
    } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineTracks from '../TimelineTracks/TimelineTracks.svelte';
    import TrackTimelineRows from '../TrackTimelineRows/TrackTimelineRows.svelte';
    import { getTimelineViewport } from '../TimelineViewport';
    import { useTrackRowsHeight } from '../TrackTimelineRows/TrackRowsResizer';
    import { untrack } from 'svelte';

    interface Props {
        ticks: TickView[];
        tracks: SequenceTrackView[];
        currentTick: number;
        selectedAnnotationId: string | null;
        bufferedRanges: ReadonlyArray<{ startIndex: number; endIndex: number }>;
        onSelectTick: (seqNumber: number) => void;
        onSelectAnnotation: (annotationId: string) => void;
        onStartTrack?: () => void;
        onAddTrack?: () => void;
        isAddingTrack?: boolean;
        onDeleteTrack?: (track: SequenceTrackView) => Promise<unknown>;
        sequenceId?: string;
        onExtendTrack?: (
            track: SequenceTrackView,
            startSeqNumber: number,
            endSeqNumber: number
        ) => void;
        onSeekStart?: () => void;
        onSeekEnd?: () => void;
        showFrameTags?: boolean;
        onShowFrameTagsChange?: (checked: boolean) => void;
        frameTags?: TickTagView[];
    }

    let {
        ticks,
        tracks,
        currentTick,
        selectedAnnotationId,
        bufferedRanges,
        onSelectTick,
        onSelectAnnotation,
        onStartTrack,
        onAddTrack,
        isAddingTrack = false,
        onExtendTrack,
        onDeleteTrack,
        sequenceId,
        onSeekStart,
        onSeekEnd,
        showFrameTags,
        onShowFrameTagsChange,
        frameTags
    }: Props = $props();
    const viewport = getTimelineViewport();
    const rowsHeight = useTrackRowsHeight();
    let container = $state<HTMLElement | null>(null);
    let content = $state<HTMLElement | null>(null);
    let previewTick = $state<number | null>(null);
    const activeIndex = $derived(
        ticks.findIndex((tick) => tick.seq_number === (previewTick ?? currentTick))
    );

    $effect(() => {
        const element = container;
        if (!element) return;
        element.scrollLeft = viewport.offset * element.scrollWidth;
    });

    // One element scrolls both ways, so the ruler, the toolbar and the row labels can be sticky.
    // Its height limit is the rows height plus the height of the sticky header above the rows.
    let headerHeight = $state(0);
    const measureHeader = () => {
        const body = content?.querySelector('[data-timeline-body]');
        if (!content || !body) return;
        headerHeight = body.getBoundingClientRect().top - content.getBoundingClientRect().top;
    };
    $effect(() => {
        const element = content;
        if (!element) return;
        measureHeader();
        const observer = new ResizeObserver(measureHeader);
        observer.observe(element);
        return () => observer.disconnect();
    });
    const getRowsRenderedHeight = () =>
        container ? Math.max(0, container.clientHeight - headerHeight) : 0;

    const syncViewportFromScroll = () => {
        if (!container || container.scrollWidth === 0) return;
        viewport.setOffset(container.scrollLeft / container.scrollWidth);
    };

    // Keep the current frame in view while zoomed, so navigation and playback both follow it.
    $effect(() => {
        const index = ticks.findIndex((tick) => tick.seq_number === currentTick);
        if (index >= 0) untrack(() => viewport.reveal(index));
    });

    // Ctrl/Cmd + wheel zooms around the cursor; a horizontal wheel pans. Registered manually
    // because the listener must be non-passive to stop the page from scrolling or zooming.
    $effect(() => {
        const element = container;
        if (!element) return;
        const onWheel = (event: WheelEvent) => {
            const width = element.clientWidth;
            if (width === 0) return;
            if (event.ctrlKey || event.metaKey) {
                event.preventDefault();
                const anchor = (event.clientX - element.getBoundingClientRect().left) / width;
                viewport.zoomBy(Math.exp(-event.deltaY * 0.01), Math.min(1, Math.max(0, anchor)));
            } else if (event.shiftKey && viewport.zoom > 1) {
                event.preventDefault();
                element.scrollLeft += event.deltaY || event.deltaX;
            }
        };
        element.addEventListener('wheel', onWheel, { passive: false });
        return () => element.removeEventListener('wheel', onWheel);
    });
</script>

<div
    class="scrollbar-thin shrink-0 overflow-auto overscroll-contain"
    style:max-height={`${rowsHeight.height + headerHeight}px`}
    bind:this={container}
    onscroll={syncViewportFromScroll}
    data-testid="timeline-scroll-container"
>
    <div class="relative" style:width={`${viewport.zoom * 100}%`} bind:this={content}>
        <TimelineTracks
            {ticks}
            {currentTick}
            {bufferedRanges}
            {onSelectTick}
            onPreviewTick={(tick) => (previewTick = tick)}
            {onSeekStart}
            {onSeekEnd}
        />
        <TrackTimelineRows
            {ticks}
            {tracks}
            {selectedAnnotationId}
            {onSelectAnnotation}
            {onSelectTick}
            {onStartTrack}
            {onAddTrack}
            {isAddingTrack}
            {onExtendTrack}
            {onDeleteTrack}
            {sequenceId}
            onExtendStart={onSeekStart}
            onExtendEnd={onSeekEnd}
            {showFrameTags}
            {onShowFrameTagsChange}
            {frameTags}
            {rowsHeight}
            {getRowsRenderedHeight}
        />
        {#if activeIndex >= 0 && ticks.length > 0}
            <div
                class="pointer-events-none absolute inset-x-2 bottom-1 top-3.5 z-30 overflow-hidden px-1"
                aria-hidden="true"
            >
                <div class="relative h-full w-full">
                    <span
                        class="absolute inset-y-0 w-px -translate-x-1/2 bg-primary"
                        style:left={`${((activeIndex + 0.5) / ticks.length) * 100}%`}
                        data-testid="timeline-playhead"
                    ></span>
                </div>
            </div>
        {/if}
    </div>
</div>
