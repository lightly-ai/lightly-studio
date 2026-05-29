import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useSelectClassDialog } from './useSelectClassDialog';

describe('useSelectClassDialog', () => {
    it('starts closed', () => {
        const dialog = useSelectClassDialog();

        expect(get(dialog.open)).toBe(false);
    });

    it('opens the dialog when requestLabel is called', () => {
        const dialog = useSelectClassDialog();

        dialog.requestLabel();

        expect(get(dialog.open)).toBe(true);
    });

    it('resolves the pending promise with the chosen label on confirm', async () => {
        const dialog = useSelectClassDialog();

        const labelPromise = dialog.requestLabel();
        dialog.handleConfirm('dog');

        await expect(labelPromise).resolves.toBe('dog');
        expect(get(dialog.open)).toBe(false);
    });

    it('resolves the pending promise with null on cancel', async () => {
        const dialog = useSelectClassDialog();

        const labelPromise = dialog.requestLabel();
        dialog.handleCancel();

        await expect(labelPromise).resolves.toBeNull();
        expect(get(dialog.open)).toBe(false);
    });

    it('shares the in-flight promise across concurrent callers', async () => {
        const dialog = useSelectClassDialog();

        const firstPromise = dialog.requestLabel();
        const secondPromise = dialog.requestLabel();

        expect(secondPromise).toBe(firstPromise);

        dialog.handleConfirm('cat');

        await expect(firstPromise).resolves.toBe('cat');
        await expect(secondPromise).resolves.toBe('cat');
    });

    it('creates a fresh promise for the next request after settling', async () => {
        const dialog = useSelectClassDialog();

        const firstPromise = dialog.requestLabel();
        dialog.handleConfirm('dog');
        await firstPromise;

        const secondPromise = dialog.requestLabel();

        expect(secondPromise).not.toBe(firstPromise);
        expect(get(dialog.open)).toBe(true);

        dialog.handleCancel();

        await expect(secondPromise).resolves.toBeNull();
    });
});
