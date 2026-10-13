import type { WorkspaceTool } from '$lib/components/PointCloudLabelingWorkspace/domain';

interface CuboidIntersection {
    annotationId: string;
    volume: number;
}

interface CuboidSelectionListenerParams {
    canvas: HTMLCanvasElement;
    activeTool: WorkspaceTool;
    onselect?: (annotationId: string | null) => void;
    onhover?: (annotationId: string | null, handle: null) => void;
    isCuboidClicked: () => boolean;
    resetCuboidClicked: () => void;
}

/**
 * Among all raycast hits, returns the annotation ID of the cuboid with the smallest volume.
 * Returns null when the list is empty.
 *
 * @param intersections - Cuboids intersected by the pointer ray.
 * @returns Annotation ID of the smallest intersected cuboid, or null.
 */
export function pickSmallestFromIntersections(intersections: CuboidIntersection[]): string | null {
    if (intersections.length === 0) return null;
    return intersections.reduce((min, curr) => (curr.volume < min.volume ? curr : min))
        .annotationId;
}

/**
 * Attaches keyboard and pointer handlers for cuboid selection and hover.
 *
 * @param params - Canvas element, active tool, and selection/hover callbacks.
 * @returns A function that removes the registered event listeners.
 */
export function addCuboidSelectionListeners({
    canvas,
    activeTool,
    onselect,
    onhover,
    isCuboidClicked,
    resetCuboidClicked
}: CuboidSelectionListenerParams): () => void {
    function onKeyDown(event: KeyboardEvent): void {
        if (event.key === 'Escape' && activeTool === 'select') onselect?.(null);
    }

    function onClick(): void {
        queueMicrotask(() => {
            if (activeTool === 'select' && !isCuboidClicked()) onselect?.(null);
            resetCuboidClicked();
        });
    }

    function onPointerLeave(): void {
        onhover?.(null, null);
    }

    window.addEventListener('keydown', onKeyDown);
    canvas.addEventListener('click', onClick);
    canvas.addEventListener('pointerleave', onPointerLeave);

    return () => {
        window.removeEventListener('keydown', onKeyDown);
        canvas.removeEventListener('click', onClick);
        canvas.removeEventListener('pointerleave', onPointerLeave);
    };
}
