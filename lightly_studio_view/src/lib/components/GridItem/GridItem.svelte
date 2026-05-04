<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import type { Snippet } from 'svelte';
    import GridItemTag from './GridItemTag.svelte';

    export type GridItemDragData = {
        url: string;
        fileName: string;
    };

    const GRID_IMAGE_SEARCH_DROP_EVENT = 'lightly:grid-image-search-drop';
    const GRID_IMAGE_SEARCH_DRAG_STATE_EVENT = 'lightly:grid-image-search-drag-state';
    const GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR = '[data-grid-search-drop-target]';
    const DRAG_START_THRESHOLD_PX = 8;
    const DRAG_PREVIEW_OFFSET_PX = 14;
    const DRAG_INACTIVITY_TIMEOUT_MS = 8000;

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
    let dragCleanupTimeout: number | null = null;
    let isPointerDragging = $state(false);
    let isOverSearchDropTarget = $state(false);
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
        window.setTimeout(() => {
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

    function clearDragCleanupTimeout() {
        if (dragCleanupTimeout) {
            window.clearTimeout(dragCleanupTimeout);
            dragCleanupTimeout = null;
        }
    }

    function scheduleDragCleanupTimeout() {
        clearDragCleanupTimeout();
        dragCleanupTimeout = window.setTimeout(() => {
            stopDragging();
        }, DRAG_INACTIVITY_TIMEOUT_MS);
    }

    function dispatchDragState(event: PointerEvent | null) {
        const isOverDropTarget = event ? Boolean(getSearchDropTarget(event)) : false;
        if (isOverSearchDropTarget === isOverDropTarget && event) {
            return;
        }

        isOverSearchDropTarget = isOverDropTarget;
        window.dispatchEvent(
            new CustomEvent(GRID_IMAGE_SEARCH_DRAG_STATE_EVENT, {
                detail: {
                    active: Boolean(event),
                    overDropTarget: isOverDropTarget
                }
            })
        );
    }

    function updateDragPreview(event: PointerEvent) {
        dragPreview = { x: event.clientX, y: event.clientY };
        dispatchDragState(event);
        scheduleDragCleanupTimeout();
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
        clearDragCleanupTimeout();
        releaseCapturedPointer();
        pointerStart = null;
        isPointerDragging = false;
        dragPreview = null;
        setBodyDraggingCursor(false);
        dispatchDragState(null);
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
        if (isPointerDragging || getPointerDistance(event) < DRAG_START_THRESHOLD_PX) {
            if (isPointerDragging) {
                updateDragPreview(event);
            }
            return;
        }

        isPointerDragging = true;
        suppressNextSelectionClick();
        setBodyDraggingCursor(true);
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

    function handleWindowPointerEnd(event: PointerEvent) {
        if (!pointerStart || pointerStart.id !== event.pointerId) {
            return;
        }
        stopDragging();
    }

    function handleWindowBlur() {
        stopDragging();
    }

    function handleVisibilityChange() {
        if (document.visibilityState === 'hidden') {
            stopDragging();
        }
    }

    function handleWindowKeyDown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            stopDragging();
        }
    }

    onMount(() => {
        window.addEventListener('pointerup', handleWindowPointerEnd);
        window.addEventListener('pointercancel', handleWindowPointerEnd);
        window.addEventListener('blur', handleWindowBlur);
        window.addEventListener('keydown', handleWindowKeyDown);
        document.addEventListener('visibilitychange', handleVisibilityChange);
    });

    onDestroy(() => {
        window.removeEventListener('pointerup', handleWindowPointerEnd);
        window.removeEventListener('pointercancel', handleWindowPointerEnd);
        window.removeEventListener('blur', handleWindowBlur);
        window.removeEventListener('keydown', handleWindowKeyDown);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
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
        class="pointer-events-none fixed z-50 h-20 w-20 overflow-hidden rounded-md border border-primary/60 bg-background shadow-xl ring-2 ring-primary/30"
        class:opacity-90={isOverSearchDropTarget}
        class:opacity-70={!isOverSearchDropTarget}
        style="left: {dragPreview.x + DRAG_PREVIEW_OFFSET_PX}px; top: {dragPreview.y +
            DRAG_PREVIEW_OFFSET_PX}px;"
        data-testid="grid-item-drag-preview"
    >
        <img src={dragData.url} alt="" class="h-full w-full object-cover" draggable="false" />
    </div>
{/if}
