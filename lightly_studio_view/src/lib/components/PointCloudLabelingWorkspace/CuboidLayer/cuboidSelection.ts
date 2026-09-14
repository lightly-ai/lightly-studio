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

interface CuboidDeleteListenerParams {
    selectedAnnotationId: string | null;
    oncuboiddelete?: (annotationId: string) => void;
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

    const target = canvas.parentElement ?? canvas;
    window.addEventListener('keydown', onKeyDown);
    target.addEventListener('click', onClick);
    return () => {
        window.removeEventListener('keydown', onKeyDown);
        target.removeEventListener('click', onClick);
    };
}

/**
 * Attaches a keydown handler that fires `oncuboiddelete` when Delete or Backspace
 * is pressed while a cuboid is selected.
 *
 * @param params - Currently selected annotation ID and delete callback.
 * @returns A function that removes the registered event listener.
 */
export function addCuboidDeleteListeners({
    selectedAnnotationId,
    oncuboiddelete
}: CuboidDeleteListenerParams): () => void {
    function onKeyDown(event: KeyboardEvent): void {
        if ((event.key === 'Delete' || event.key === 'Backspace') && selectedAnnotationId) {
            oncuboiddelete?.(selectedAnnotationId);
        }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => {
        window.removeEventListener('keydown', onKeyDown);
    };
}
