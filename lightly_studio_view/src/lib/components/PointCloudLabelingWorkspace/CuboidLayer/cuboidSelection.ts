import type { WorkspaceTool } from '$lib/components/PointCloudLabelingWorkspace/domain';

interface SelectCuboidParams {
    annotationId: string;
    activeTool: WorkspaceTool;
    onselect?: (annotationId: string | null) => void;
}

interface CuboidSelectionListenerParams {
    canvas: HTMLCanvasElement;
    activeTool: WorkspaceTool;
    onselect?: (annotationId: string | null) => void;
    isCuboidClicked: () => boolean;
    resetCuboidClicked: () => void;
}

/**
 * Selects a cuboid when selection is the active workspace tool.
 *
 * @param params - Cuboid identity, active tool, and selection callback.
 * @returns Whether the cuboid was selected.
 */
export function selectCuboid({ annotationId, activeTool, onselect }: SelectCuboidParams): boolean {
    if (activeTool !== 'select') return false;
    onselect?.(annotationId);
    return true;
}

/**
 * Attaches keyboard and empty-canvas handlers for select-mode deselection.
 *
 * @param params - Canvas element, current interaction state, and selection callbacks.
 * @returns A function that removes the registered event listeners.
 */
export function addCuboidSelectionListeners({
    canvas,
    activeTool,
    onselect,
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

    window.addEventListener('keydown', onKeyDown);
    canvas.addEventListener('click', onClick);
    return () => {
        window.removeEventListener('keydown', onKeyDown);
        canvas.removeEventListener('click', onClick);
    };
}
