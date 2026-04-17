import { describe, expect, it, vi } from 'vitest';
import { usePendingSaveTokens } from './usePendingSaveTokens';

describe('usePendingSaveTokens', () => {
    it('starts pending and emits unique prefixed tokens', () => {
        const onPendingChange = vi.fn();
        const { startPending } = usePendingSaveTokens({
            tokenPrefix: 'brush',
            onPendingChange
        });

        const token1 = startPending();
        const token2 = startPending();

        expect(token1).toBe('brush-1');
        expect(token2).toBe('brush-2');
        expect(onPendingChange).toHaveBeenNthCalledWith(1, {
            token: 'brush-1',
            isPending: true
        });
        expect(onPendingChange).toHaveBeenNthCalledWith(2, {
            token: 'brush-2',
            isPending: true
        });
    });

    it('ends pending only for known tokens', () => {
        const onPendingChange = vi.fn();
        const { startPending, endPending } = usePendingSaveTokens({
            tokenPrefix: 'eraser',
            onPendingChange
        });

        const token = startPending();
        endPending('eraser-999');
        endPending(token);
        endPending(token);

        expect(onPendingChange).toHaveBeenCalledTimes(2);
        expect(onPendingChange).toHaveBeenNthCalledWith(1, {
            token: 'eraser-1',
            isPending: true
        });
        expect(onPendingChange).toHaveBeenNthCalledWith(2, {
            token: 'eraser-1',
            isPending: false
        });
    });

    it('resets all active pending tokens and clears internal state', () => {
        const onPendingChange = vi.fn();
        const { startPending, endPending, resetPending } = usePendingSaveTokens({
            tokenPrefix: 'bbox',
            onPendingChange
        });

        const token1 = startPending();
        const token2 = startPending();
        endPending(token1);
        resetPending();
        resetPending();

        expect(onPendingChange).toHaveBeenCalledTimes(4);
        expect(onPendingChange).toHaveBeenNthCalledWith(4, {
            token: token2,
            isPending: false
        });
    });

    it('works without an onPendingChange callback', () => {
        const { startPending, endPending, resetPending } = usePendingSaveTokens({
            tokenPrefix: 'brush'
        });

        const token = startPending();
        expect(() => endPending(token)).not.toThrow();
        expect(() => resetPending()).not.toThrow();
    });
});
