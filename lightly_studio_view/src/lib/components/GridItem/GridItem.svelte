<script lang="ts">
    import { onDestroy } from 'svelte';
    import type { Snippet } from 'svelte';
    import GridItemTag from './GridItemTag.svelte';
    import {
        GRID_IMAGE_SEARCH_DROP_EVENT,
        type GridItemDragData
    } from './GridItem.constants';
    const GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR = '[data-grid-search-drop-target]';
    const DRAG_START_THRESHOLD_PX = 8;
    const DRAG_PREVIEW_OFFSET_PX = 14;

    let {
        children,
        width = 300,
        height = 300,
        style,
        dataTestId,
        ariaLabel = 'View item',
        isSelected = false,
        tag = true,
        caption,
        dataSampleName,
        dataIndex,
        dragData,
        onSelect,
        ondblclick
    }: {
        children: Snippet;
        width?: string | number;
        height?: string | number;
        style?: string;
        dataTestId?: string;
        ariaLabel?: string;
        isSelected?: boolean;
        tag?: boolean;
        caption?: string;
        dataSampleName?: string;
        dataIndex?: number;
        dragData?: GridItemDragData;
        onSelect?: (event: MouseEvent | KeyboardEvent) => void;
        ondblclick?: (event: MouseEvent) => void;
    } = $props();

    let suppressNextClick = false;
    let pointerStart: { x: number; y: number; id: number } | null = null;
    let capturedPointerElement: HTMLElement | null = null;
    let isPointerDragging = $state(false);
    let dragPreview = $state<{ x: number; y: number } | null>(null);

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }

    function handleOnClick(event: MouseEvent) {
        if (!onSelect) return;
        if (suppressNextClick) {
            suppressNextClick = false;
            event.preventDefault();
            return;
        }
        event.preventDefault();
        onSelect(event);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (!onSelect) return;
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        onSelect(event);
    }

    function suppressNextSelectionClick() {
        suppressNextClick = true;
        setTimeout(() => {
            suppressNextClick = false;
        }, 100);
    }

    function getPointerDistance(event: PointerEvent): number {
        if (!pointerStart) {
            return 0;
        }
        return Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y);
    }

    function getPointerTarget(event: PointerEvent): HTMLElement | null {
        return event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
    }

    function getSearchDropTarget(event: PointerEvent): Element | null {
        return (
            document
                .elementFromPoint(event.clientX, event.clientY)
                ?.closest(GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR) ?? null
        );
    }

    function setBodyDraggingCursor(isDragging: boolean) {
        document.body.style.cursor = isDragging ? 'grabbing' : '';
    }

    function updateDragPreview(event: PointerEvent) {
        dragPreview = { x: event.clientX, y: event.clientY };
    }

    function releaseCapturedPointer(pointerId = pointerStart?.id) {
        if (capturedPointerElement && pointerId != null) {
            try {
                if (capturedPointerElement.hasPointerCapture?.(pointerId)) {
                    capturedPointerElement.releasePointerCapture(pointerId);
                }
            } catch {
                // Pointer capture may already be gone when cleanup races browser events.
            }
        }
        capturedPointerElement = null;
    }

    function stopDragging() {
        releaseCapturedPointer();
        pointerStart = null;
        isPointerDragging = false;
        dragPreview = null;
        setBodyDraggingCursor(false);
    }

    function handlePointerDown(event: PointerEvent) {
        if (!dragData || event.button !== 0) {
            return;
        }
        pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
        isPointerDragging = false;
        capturedPointerElement = getPointerTarget(event);
        capturedPointerElement?.setPointerCapture?.(event.pointerId);
    }

    function handlePointerMove(event: PointerEvent) {
        if (!dragData || !pointerStart || pointerStart.id !== event.pointerId) {
            return;
        }
        if (!isPointerDragging && getPointerDistance(event) < DRAG_START_THRESHOLD_PX) {
            return;
        }
        if (!isPointerDragging) {
            isPointerDragging = true;
            suppressNextSelectionClick();
            setBodyDraggingCursor(true);
        }
        updateDragPreview(event);
    }

    function handlePointerUp(event: PointerEvent) {
        if (!dragData || !pointerStart || pointerStart.id !== event.pointerId) {
            stopDragging();
            return;
        }

        const dropTarget = isPointerDragging ? getSearchDropTarget(event) : null;

        if (isPointerDragging) {
            suppressNextSelectionClick();
        }

        stopDragging();

        if (dropTarget) {
            window.dispatchEvent(
                new CustomEvent<GridItemDragData>(GRID_IMAGE_SEARCH_DROP_EVENT, {
                    detail: dragData
                })
            );
        }
    }

    function handlePointerCancel() {
        stopDragging();
    }

    function handleLostPointerCapture() {
        stopDragging();
    }

    onDestroy(() => {
        stopDragging();
    });
</script>

<div class="select-none" {style}>
    <div
        class="relative overflow-hidden rounded-lg dark:[color-scheme:dark]"
        class:grid-item-selected={isSelected}
        style="width: {formatSize(width)}; height: {formatSize(height)};"
        data-testid={dataTestId}
        data-sample-name={dataSampleName}
        data-index={dataIndex}
        draggable="false"
        class:cursor-grab={dragData && !isPointerDragging}
        class:cursor-grabbing={isPointerDragging}
        {ondblclick}
        onclick={handleOnClick}
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={handlePointerUp}
        onpointercancel={handlePointerCancel}
        onlostpointercapture={handleLostPointerCapture}
        onkeydown={handleKeyDown}
        aria-label={ariaLabel}
        role="button"
        tabindex="0"
    >
        {#if tag}
            <GridItemTag {isSelected} />
        {/if}

        {@render children()}

        {#if caption}
            <div
                class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
                data-testid="grid-item-caption"
            >
                <span class="block truncate" title={caption} data-testid="grid-item-caption-text">
                    {caption}
                </span>
            </div>
        {/if}
    </div>
</div>

{#if dragData && dragPreview}
    <div
        class="pointer-events-none fixed z-50 h-20 w-20 overflow-hidden rounded-md border border-primary/60 bg-background opacity-80 shadow-xl ring-2 ring-primary/30"
        style="left: {dragPreview.x + DRAG_PREVIEW_OFFSET_PX}px; top: {dragPreview.y +
            DRAG_PREVIEW_OFFSET_PX}px;"
        data-testid="grid-item-drag-preview"
    >
        <img src={dragData.url} alt="" class="h-full w-full object-cover" draggable="false" />
    </div>
{/if}
