import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SimilarityThresholdSlider from './SimilarityThresholdSlider.svelte';

const onCommit = vi.fn();
const onClear = vi.fn();
const defaultProps = { range: { min: -0.1, max: 0.3 }, value: null, onCommit, onClear };

const pressKey = (key: string) => fireEvent.keyDown(screen.getByRole('slider'), { key });

describe('SimilarityThresholdSlider', () => {
    beforeEach(() => {
        onCommit.mockClear();
        onClear.mockClear();
    });

    it('shows the range minimum and maximum and no number input when off', () => {
        render(SimilarityThresholdSlider, { props: defaultProps });

        expect(screen.getByText('-0.1')).toBeInTheDocument();
        expect(screen.getByText('0.3')).toBeInTheDocument();
        expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
        expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '0');
    });

    it('shows the current threshold', () => {
        render(SimilarityThresholdSlider, { props: { ...defaultProps, value: 0.1 } });

        expect(screen.getByText('0.1')).toBeInTheDocument();
        expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '500');
    });

    it('commits a threshold one step above the minimum', async () => {
        render(SimilarityThresholdSlider, { props: defaultProps });

        await pressKey('ArrowRight');

        expect(onCommit).toHaveBeenCalledOnce();
        expect(onCommit.mock.calls[0][0]).toBeCloseTo(-0.0996);
    });

    it('commits the range maximum at the end', async () => {
        render(SimilarityThresholdSlider, { props: defaultProps });

        await pressKey('End');

        expect(onCommit).toHaveBeenCalledExactlyOnceWith(0.3);
    });

    it('clears the threshold at the range minimum', async () => {
        render(SimilarityThresholdSlider, { props: { ...defaultProps, value: 0.1 } });

        await pressKey('Home');

        expect(onClear).toHaveBeenCalledOnce();
        expect(onCommit).not.toHaveBeenCalled();
    });

    it('follows a reset of the value', async () => {
        const { rerender } = render(SimilarityThresholdSlider, {
            props: { ...defaultProps, value: 0.1 }
        });

        await rerender({ ...defaultProps, value: null });

        expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '0');
    });
});
