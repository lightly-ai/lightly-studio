import { toast } from 'svelte-sonner';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSelectionUndo } from './useSelectionUndo';

vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(() => 't1'), error: vi.fn(), dismiss: vi.fn() }
}));

const pressZ = () => new KeyboardEvent('keydown', { key: 'z', cancelable: true });

describe('useSelectionUndo', () => {
    afterEach(() => {
        vi.clearAllMocks();
        document.body.innerHTML = '';
    });

    it('Z runs the offered undo once and closes the toast', async () => {
        const revert = vi.fn().mockResolvedValue(undefined);
        const { offerUndo, handleUndoKey } = useSelectionUndo();
        offerUndo({ message: "Added 'a' to 2 items", revert });

        expect(handleUndoKey(pressZ())).toBe(true);
        await vi.waitFor(() => expect(revert).toHaveBeenCalledOnce());
        expect(toast.dismiss).toHaveBeenCalledWith('t1');
        await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Undone'));
        expect(handleUndoKey(pressZ())).toBe(false);
    });

    it('ignores Z while a text field has focus', () => {
        const revert = vi.fn().mockResolvedValue(undefined);
        const { offerUndo, handleUndoKey } = useSelectionUndo();
        offerUndo({ message: "Added 'a' to 2 items", revert });
        const input = document.createElement('input');
        document.body.appendChild(input);
        input.focus();

        expect(handleUndoKey(pressZ())).toBe(false);
        expect(revert).not.toHaveBeenCalled();
    });
});
