import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { useDeleteSelectedCuboidShortcut } from './useDeleteSelectedCuboidShortcut.svelte';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const disposers: (() => void)[] = [];
afterEach(() => {
    disposers.splice(0).forEach((dispose) => dispose());
    document.body.replaceChildren();
});

function setup({
    selectedCuboidId = 'cuboid-1' as string | null,
    isEditingMode = true,
    isTickStale = false,
    deleteCuboid = vi.fn().mockResolvedValue(undefined)
} = {}) {
    disposers.push(
        $effect.root(() => {
            useDeleteSelectedCuboidShortcut({
                getSelectedCuboidId: () => selectedCuboidId,
                getIsEditingMode: () => isEditingMode,
                getIsTickStale: () => isTickStale,
                deleteCuboid
            });
        })
    );
    flushSync();
    return { deleteCuboid };
}

function pressKey(key: string, target: EventTarget = window, init: KeyboardEventInit = {}) {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
    target.dispatchEvent(event);
    return event;
}

describe('useDeleteSelectedCuboidShortcut', () => {
    it('deletes the selected cuboid with Delete and Backspace', () => {
        const { deleteCuboid } = setup();

        const deleteEvent = pressKey('Delete');
        pressKey('Backspace');

        expect(deleteCuboid.mock.calls).toEqual([['cuboid-1'], ['cuboid-1']]);
        expect(deleteEvent.defaultPrevented).toBe(true);
    });

    it('shows an error when the refresh after the delete fails', async () => {
        setup({ deleteCuboid: vi.fn().mockRejectedValue(new Error('refresh failed')) });

        pressKey('Delete');
        await vi.waitFor(() => expect(toast.error).toHaveBeenCalled());
    });

    it('does nothing outside edit mode', () => {
        const { deleteCuboid } = setup({ isEditingMode: false });

        pressKey('Delete');

        expect(deleteCuboid).not.toHaveBeenCalled();
    });

    it('does nothing while the next tick loads', () => {
        const { deleteCuboid } = setup({ isTickStale: true });

        pressKey('Delete');

        expect(deleteCuboid).not.toHaveBeenCalled();
    });

    it('does nothing without a selected cuboid', () => {
        const { deleteCuboid } = setup({ selectedCuboidId: null });

        const event = pressKey('Delete');

        expect(deleteCuboid).not.toHaveBeenCalled();
        expect(event.defaultPrevented).toBe(false);
    });

    it('does nothing while typing in an input or with a modifier key', () => {
        const { deleteCuboid } = setup();
        const input = document.createElement('input');
        document.body.append(input);

        pressKey('Backspace', input);
        pressKey('Backspace', window, { metaKey: true });
        pressKey('Delete', window, { repeat: true });

        expect(deleteCuboid).not.toHaveBeenCalled();
    });

    it('does nothing inside a dialog', () => {
        const { deleteCuboid } = setup();
        const dialog = document.createElement('div');
        dialog.setAttribute('role', 'dialog');
        const button = document.createElement('button');
        dialog.append(button);
        document.body.append(dialog);

        pressKey('Delete', button);

        expect(deleteCuboid).not.toHaveBeenCalled();
    });
});
