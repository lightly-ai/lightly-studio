import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TimelineBufferStatus from './TimelineBufferStatus.svelte';

const defaultStatus = {
    isWaiting: false,
    failedCount: 0,
    isRetrying: false,
    onRetry: vi.fn().mockResolvedValue(undefined)
};

describe('TimelineBufferStatus', () => {
    it('announces waiting and clears the message when playback can resume', async () => {
        const { rerender } = render(TimelineBufferStatus, {
            status: { ...defaultStatus, isWaiting: true }
        });
        expect(screen.getByRole('status')).toHaveTextContent('Buffering…');

        await rerender({ status: defaultStatus });

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('offers recovery for failed frames and disables duplicate retries', async () => {
        const onRetry = vi.fn().mockResolvedValue(undefined);
        const status = { ...defaultStatus, isWaiting: true, failedCount: 2, onRetry };
        const { rerender } = render(TimelineBufferStatus, { status });
        expect(screen.getByRole('status')).toHaveTextContent('2 frames failed to load.');

        await fireEvent.click(screen.getByRole('button', { name: 'Retry failed frames' }));
        expect(onRetry).toHaveBeenCalledOnce();
        await rerender({ status: { ...status, isRetrying: true } });

        expect(screen.getByRole('status')).toHaveTextContent('Retrying failed frames…');
        expect(screen.getByRole('button', { name: 'Retry failed frames' })).toBeDisabled();
    });
});
