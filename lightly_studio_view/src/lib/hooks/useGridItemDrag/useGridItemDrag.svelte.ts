import { onDestroy } from 'svelte';
import {
    GRID_IMAGE_SEARCH_DROP_EVENT,
    GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR,
    DRAG_START_THRESHOLD_PX,
    type GridItemDragData
} from '$lib/components/GridItem/GridItem.constants';

export function useGridItemDrag(getDragData: () => GridItemDragData | undefined) {
    let suppressNextClick = $state(false);
    let pointerStart: { x: number; y: number; id: number } | null = null;
    let capturedPointerElement: HTMLElement | null = null;
    let isPointerDragging = $state(false);
    let dragPreview = $state<{ x: number; y: number } | null>(null);

    function suppressNextSelectionClick() {
        suppressNextClick = true;
        setTimeout(() => {
            suppressNextClick = false;
        }, 100);
    }

    function getPointerDistance(event: PointerEvent): number {
        if (!pointerStart) return 0;
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
        const dragData = getDragData();
        if (!dragData || event.button !== 0) return;
        pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
        isPointerDragging = false;
        capturedPointerElement = getPointerTarget(event);
        capturedPointerElement?.setPointerCapture?.(event.pointerId);
    }

    function handlePointerMove(event: PointerEvent) {
        if (!getDragData() || !pointerStart || pointerStart.id !== event.pointerId) return;
        if (!isPointerDragging && getPointerDistance(event) < DRAG_START_THRESHOLD_PX) return;
        if (!isPointerDragging) {
            isPointerDragging = true;
            suppressNextSelectionClick();
            setBodyDraggingCursor(true);
        }
        updateDragPreview(event);
    }

    function handlePointerUp(event: PointerEvent) {
        const dragData = getDragData();
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

    return {
        get isPointerDragging() {
            return isPointerDragging;
        },
        get dragPreview() {
            return dragPreview;
        },
        get suppressNextClick() {
            return suppressNextClick;
        },
        set suppressNextClick(v: boolean) {
            suppressNextClick = v;
        },
        handlePointerDown,
        handlePointerMove,
        handlePointerUp,
        handlePointerCancel,
        handleLostPointerCapture
    };
}
