import { describe, expect, it, vi } from 'vitest';
import { usePendingOperations } from './usePendingOperations';

describe('usePendingOperations', () => {
    it('starts pending and emits unique prefixed operations', () => {
        const onPendingChange = vi.fn();
        const { startPending } = usePendingOperations({
            operationPrefix: 'brush',
            onPendingChange
        });

        const operation1 = startPending();
        const operation2 = startPending();

        expect(operation1).toBe('brush-1');
        expect(operation2).toBe('brush-2');
        expect(onPendingChange).toHaveBeenNthCalledWith(1, {
            operation: 'brush-1',
            isPending: true
        });
        expect(onPendingChange).toHaveBeenNthCalledWith(2, {
            operation: 'brush-2',
            isPending: true
        });
    });

    it('ends pending only for known operations', () => {
        const onPendingChange = vi.fn();
        const { startPending, endPending } = usePendingOperations({
            operationPrefix: 'eraser',
            onPendingChange
        });

        const operation = startPending();
        endPending('eraser-999');
        endPending(operation);
        endPending(operation);

        expect(onPendingChange).toHaveBeenCalledTimes(2);
        expect(onPendingChange).toHaveBeenNthCalledWith(1, {
            operation: 'eraser-1',
            isPending: true
        });
        expect(onPendingChange).toHaveBeenNthCalledWith(2, {
            operation: 'eraser-1',
            isPending: false
        });
    });

    it('resets all active pending operations and clears internal state', () => {
        const onPendingChange = vi.fn();
        const { startPending, endPending, resetPending } = usePendingOperations({
            operationPrefix: 'bbox',
            onPendingChange
        });

        const operation1 = startPending();
        const operation2 = startPending();
        endPending(operation1);
        resetPending();
        resetPending();

        expect(onPendingChange).toHaveBeenCalledTimes(4);
        expect(onPendingChange).toHaveBeenNthCalledWith(4, {
            operation: operation2,
            isPending: false
        });
    });

    it('works without an onPendingChange callback', () => {
        const { startPending, endPending, resetPending } = usePendingOperations({
            operationPrefix: 'brush'
        });

        const operation = startPending();
        expect(() => endPending(operation)).not.toThrow();
        expect(() => resetPending()).not.toThrow();
    });
});
