import { isTextInputTarget } from '$lib/utils';

const DELETE_KEYS = new Set(['Delete', 'Backspace']);

interface Params {
    getSelectedCuboidId: () => string | null;
    getIsEditingMode: () => boolean;
    /** While the next tick loads, the selection can still point at a cuboid of the last tick. */
    getIsTickStale: () => boolean;
    deleteCuboid: (cuboidId: string) => Promise<void>;
}

/** Deletes the selected cuboid on Delete or Backspace while the workspace is in edit mode. */
export function useDeleteSelectedCuboidShortcut({
    getSelectedCuboidId,
    getIsEditingMode,
    getIsTickStale,
    deleteCuboid
}: Params): void {
    function onKeyDown(event: KeyboardEvent): void {
        if (!isDeleteShortcut(event)) return;
        const selectedCuboidId = getSelectedCuboidId();
        if (!getIsEditingMode() || getIsTickStale() || !selectedCuboidId) return;
        event.preventDefault();
        void deleteCuboid(selectedCuboidId);
    }

    $effect(() => {
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    });
}

function isDeleteShortcut(event: KeyboardEvent): boolean {
    if (!DELETE_KEYS.has(event.key) || event.repeat) return false;
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return false;
    return !isTextInputTarget(event.target) && !isInDialog(event.target);
}

function isInDialog(target: EventTarget | null): boolean {
    return target instanceof Element && target.closest('[role="dialog"]') !== null;
}
