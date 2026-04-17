import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { usePendingSaveState } from './usePendingSaveState';

describe('usePendingSaveState', () => {
    it('starts empty', () => {
        const { pendingSaveTokens, isSavePending } = usePendingSaveState();

        expect(get(pendingSaveTokens)).toEqual([]);
        expect(get(isSavePending)).toBe(false);
    });

    it('adds pending token and deduplicates repeated pending events', () => {
        const { pendingSaveTokens, isSavePending, handleSavePendingChange } = usePendingSaveState();

        handleSavePendingChange({ token: 'brush-1', isPending: true });
        handleSavePendingChange({ token: 'brush-1', isPending: true });

        expect(get(pendingSaveTokens)).toEqual(['brush-1']);
        expect(get(isSavePending)).toBe(true);
    });

    it('removes pending token on completion and ignores unknown tokens', () => {
        const { pendingSaveTokens, isSavePending, handleSavePendingChange } = usePendingSaveState();

        handleSavePendingChange({ token: 'brush-1', isPending: true });
        handleSavePendingChange({ token: 'eraser-1', isPending: true });
        handleSavePendingChange({ token: 'missing-1', isPending: false });
        handleSavePendingChange({ token: 'brush-1', isPending: false });

        expect(get(pendingSaveTokens)).toEqual(['eraser-1']);
        expect(get(isSavePending)).toBe(true);
    });

    it('becomes not pending when all tokens are removed', () => {
        const { pendingSaveTokens, isSavePending, handleSavePendingChange } = usePendingSaveState();

        handleSavePendingChange({ token: 'bbox-1', isPending: true });
        handleSavePendingChange({ token: 'bbox-2', isPending: true });
        handleSavePendingChange({ token: 'bbox-1', isPending: false });
        handleSavePendingChange({ token: 'bbox-2', isPending: false });

        expect(get(pendingSaveTokens)).toEqual([]);
        expect(get(isSavePending)).toBe(false);
    });
});
