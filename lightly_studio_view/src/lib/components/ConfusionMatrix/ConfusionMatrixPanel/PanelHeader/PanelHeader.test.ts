import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PanelHeader from './PanelHeader.svelte';
import type { ClassSetConfig, ColorConfig } from '../../ClassSetDialog/types';

const topNConfig: ClassSetConfig = {
    mode: 'topN',
    n: 5,
    sortBy: 'most-confused',
    manualClasses: []
};
const defaultColor: ColorConfig = { intensity: 1, logScale: true };

const defaultProps = {
    config: topNConfig,
    color: defaultColor,
    realClassCount: 80,
    visibleClassCount: 5,
    onConfigure: vi.fn(),
    onExpand: vi.fn()
};

describe('PanelHeader', () => {
    it('summarizes the top-N view and aggregation note', () => {
        render(PanelHeader, { props: { ...defaultProps } });

        expect(screen.getByText(/Top 5 of 80 classes/)).toBeInTheDocument();
        expect(screen.getByText(/sorted by most confused/)).toBeInTheDocument();
        expect(screen.getByText(/rest aggregated/)).toBeInTheDocument();
    });

    it('summarizes the manual view', () => {
        render(PanelHeader, {
            props: {
                ...defaultProps,
                config: { ...topNConfig, mode: 'manual', manualClasses: ['a', 'b'] },
                visibleClassCount: 2
            }
        });

        expect(screen.getByText(/Manual selection · 2 of 80 classes/)).toBeInTheDocument();
    });

    it('notes non-default coloring', () => {
        render(PanelHeader, {
            props: { ...defaultProps, color: { intensity: 1.5, logScale: false } }
        });

        expect(screen.getByText(/linear coloring at 1.5×/)).toBeInTheDocument();
    });

    it('exposes accessible labels and fires the control callbacks', async () => {
        const onConfigure = vi.fn();
        const onExpand = vi.fn();
        render(PanelHeader, { props: { ...defaultProps, onConfigure, onExpand } });

        const configure = screen.getByTestId('confusion-matrix-configure');
        const expand = screen.getByTestId('confusion-matrix-expand');
        expect(configure).toHaveAccessibleName('Configure class filters and colors');
        expect(expand).toHaveAccessibleName('Expand confusion matrix');

        await fireEvent.click(configure);
        await fireEvent.click(expand);
        expect(onConfigure).toHaveBeenCalledOnce();
        expect(onExpand).toHaveBeenCalledOnce();
    });
});
