import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { usePendingState } from './usePendingState';

describe('usePendingState', () => {
    it('starts empty', () => {
        const { pendingOperations, isPending } = usePendingState();

        expect(get(pendingOperations)).toEqual([]);
        expect(get(isPending)).toBe(false);
    });

    it('adds pending operation and deduplicates repeated pending events', () => {
        const { pendingOperations, isPending, handlePendingChange } = usePendingState();

        handlePendingChange({ operation: 'brush-1', isPending: true });
        handlePendingChange({ operation: 'brush-1', isPending: true });

        expect(get(pendingOperations)).toEqual(['brush-1']);
        expect(get(isPending)).toBe(true);
    });

    it('removes pending operation on completion and ignores unknown operations', () => {
        const { pendingOperations, isPending, handlePendingChange } = usePendingState();

        handlePendingChange({ operation: 'brush-1', isPending: true });
        handlePendingChange({ operation: 'eraser-1', isPending: true });
        handlePendingChange({ operation: 'missing-1', isPending: false });
        handlePendingChange({ operation: 'brush-1', isPending: false });

        expect(get(pendingOperations)).toEqual(['eraser-1']);
        expect(get(isPending)).toBe(true);
    });

    it('becomes not pending when all operations are removed', () => {
        const { pendingOperations, isPending, handlePendingChange } = usePendingState();

        handlePendingChange({ operation: 'bbox-1', isPending: true });
        handlePendingChange({ operation: 'bbox-2', isPending: true });
        handlePendingChange({ operation: 'bbox-1', isPending: false });
        handlePendingChange({ operation: 'bbox-2', isPending: false });

        expect(get(pendingOperations)).toEqual([]);
        expect(get(isPending)).toBe(false);
    });
});
