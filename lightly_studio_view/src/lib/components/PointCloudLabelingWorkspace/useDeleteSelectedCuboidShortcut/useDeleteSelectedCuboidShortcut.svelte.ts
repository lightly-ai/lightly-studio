import { isTextInputTarget } from '$lib/utils';

const DELETE_KEYS = new Set(['Delete', 'Backspace']);

interface Params {
    getSelectedCuboidId: () => string | null;
    getIsEditingMode: () => boolean;
    deleteCuboid: (cuboidId: string) => Promise<void>;
}

/** Deletes the selected cuboid on Delete or Backspace while the workspace is in edit mode. */
export function useDeleteSelectedCuboidShortcut({
    getSelectedCuboidId,
    getIsEditingMode,
    deleteCuboid
}: Params): void {
    function onKeyDown(event: KeyboardEvent): void {
        if (!DELETE_KEYS.has(event.key) || event.repeat) return;
        if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
        if (isTextInputTarget(event.target) || isInDialog(event.target)) return;
        const selectedCuboidId = getSelectedCuboidId();
        if (!getIsEditingMode() || !selectedCuboidId) return;
        event.preventDefault();
        void deleteCuboid(selectedCuboidId);
    }

    $effect(() => {
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    });
}

function isInDialog(target: EventTarget | null): boolean {
    return target instanceof Element && target.closest('[role="dialog"]') !== null;
}
