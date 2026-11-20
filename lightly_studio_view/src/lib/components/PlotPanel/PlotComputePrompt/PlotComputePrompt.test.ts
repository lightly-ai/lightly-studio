import { act, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PlotComputePrompt from './PlotComputePrompt.svelte';

const NOW = 10_000_000;

const defaultProps = {
    view: 'prompt' as const,
    embeddingCount: 2_000_000,
    itemLabel: 'image',
    startedAt: null,
    onCompute: () => {}
};

describe('PlotComputePrompt', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('renders the prompt and calls onCompute', async () => {
        const onCompute = vi.fn();
        render(PlotComputePrompt, { props: { ...defaultProps, onCompute } });

        expect(screen.getByText('Plot not computed')).toBeInTheDocument();
        expect(
            screen.getByText('2,000,000 images. The first compute can take several minutes.')
        ).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Compute plot' }));
        expect(onCompute).toHaveBeenCalledOnce();
    });

    it('names the items of the collection in the count', () => {
        render(PlotComputePrompt, { props: { ...defaultProps, itemLabel: 'video' } });

        expect(
            screen.getByText('2,000,000 videos. The first compute can take several minutes.')
        ).toBeInTheDocument();
    });

    it('renders the computing state with the elapsed time', async () => {
        vi.useFakeTimers({ now: NOW });
        render(PlotComputePrompt, {
            props: { ...defaultProps, view: 'computing', startedAt: NOW - 222_000 }
        });

        expect(screen.getByText('Computing plot…')).toBeInTheDocument();
        expect(
            screen.getByText('Running for 3:42. The first compute can take several minutes.')
        ).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Compute plot' })).not.toBeInTheDocument();

        await act(() => vi.advanceTimersByTime(1_000));

        expect(
            screen.getByText('Running for 3:43. The first compute can take several minutes.')
        ).toBeInTheDocument();
    });

    it.each([
        { view: 'prompt' as const, startedAt: null },
        { view: 'computing' as const, startedAt: NOW }
    ])('never mentions text axes in the $view view', ({ view, startedAt }) => {
        vi.useFakeTimers({ now: NOW });
        render(PlotComputePrompt, { props: { ...defaultProps, view, startedAt } });

        expect(screen.queryByText(/text axes/i)).not.toBeInTheDocument();
    });
});
