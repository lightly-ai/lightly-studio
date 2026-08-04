import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import DatasetDistributionHeader from './DatasetDistributionHeader.svelte';
import { useDistributionPanel } from './useDistributionPanel.svelte';
import type { DistributionSource } from './types';

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

const barSource = (overrides: Partial<DistributionSource> = {}): DistributionSource => ({
    id: 'classes',
    label: 'Classes',
    data: [{ label: 'car', count: 10 }],
    ...overrides
});

const histogramSource = (): DistributionSource => ({
    id: 'metadata',
    label: 'Metadata',
    valueNoun: 'samples',
    groups: [
        {
            id: 'confidence',
            label: 'confidence',
            histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
        }
    ]
});

const categoricalSource = (
    state: { loading?: boolean; error?: string } = {}
): DistributionSource => ({
    id: 'metadata',
    label: 'Metadata',
    valueNoun: 'samples',
    groups: [
        {
            id: 'city',
            label: 'city',
            categorical: {
                selectedValues: [],
                buckets: [
                    { id: 'zurich', kind: 'value', value: 'Zurich', label: 'Zurich', count: 4 },
                    { id: 'bern', kind: 'value', value: 'Bern', label: 'Bern', count: 2 }
                ],
                ...state
            }
        }
    ]
});

const defaultCallbacks = {
    onOpenConfig: vi.fn(),
    onOpenExpand: vi.fn(),
    onOpenHistogramExpand: vi.fn()
};

const renderHeader = (sources: DistributionSource[], overrides: Record<string, unknown> = {}) => {
    const panel = useDistributionPanel(() => ({ sources }));
    return render(DatasetDistributionHeader, {
        props: {
            title: 'Distribution',
            panel,
            histogramBinCount: 20,
            ...defaultCallbacks,
            ...overrides
        }
    });
};

describe('DatasetDistributionHeader', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    it('renders the title', () => {
        renderHeader([barSource()]);
        expect(screen.getByText('Distribution')).toBeInTheDocument();
    });

    it('shows a close button when onClose is provided', () => {
        const onClose = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [barSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onClose
            }
        });
        expect(screen.getByTestId('dataset-distribution-close-button')).toBeInTheDocument();
    });

    it('omits the close button when onClose is not provided', () => {
        renderHeader([barSource()]);
        expect(screen.queryByTestId('dataset-distribution-close-button')).not.toBeInTheDocument();
    });

    it('calls onClose when the close button is clicked', async () => {
        const onClose = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [barSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onClose
            }
        });
        await fireEvent.click(screen.getByTestId('dataset-distribution-close-button'));
        expect(onClose).toHaveBeenCalledOnce();
    });

    it('shows the source selector when multiple sources are provided', () => {
        renderHeader([
            barSource({ id: 'a', label: 'Source A' }),
            barSource({ id: 'b', label: 'Source B' })
        ]);
        expect(screen.getByTestId('dataset-distribution-source-select')).toBeInTheDocument();
    });

    it('omits the source selector for a single source', () => {
        renderHeader([barSource()]);
        expect(screen.queryByTestId('dataset-distribution-source-select')).not.toBeInTheDocument();
    });

    it('shows the histogram summary for a histogram group', () => {
        renderHeader([histogramSource()]);
        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples · 2 bins · 0–1'
        );
    });

    it('shows the expand button for histogram sources and calls onOpenHistogramExpand on click', async () => {
        const onOpenHistogramExpand = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [histogramSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onOpenHistogramExpand
            }
        });
        await fireEvent.click(screen.getByTestId('dataset-distribution-histogram-expand'));
        expect(onOpenHistogramExpand).toHaveBeenCalledOnce();
    });

    it('shows the class/annotation summary for bar chart data', () => {
        renderHeader([barSource()]);
        expect(screen.getByText(/1 class · sorted by count · 10 annotations/)).toBeInTheDocument();
    });

    it('calls onOpenConfig when the configure button is clicked for bar chart data', async () => {
        const onOpenConfig = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [barSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onOpenConfig
            }
        });
        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        expect(onOpenConfig).toHaveBeenCalledOnce();
    });

    it('calls onOpenExpand when the expand button is clicked for bar chart data', async () => {
        const onOpenExpand = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [barSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onOpenExpand
            }
        });
        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));
        expect(onOpenExpand).toHaveBeenCalledOnce();
    });

    it('shows the categorical value summary and configure/expand buttons', () => {
        renderHeader([categoricalSource()]);
        expect(screen.getByText(/2 values · sorted by count · 6 samples/)).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-configure')).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-expand')).toBeInTheDocument();
    });

    it('calls onOpenConfig when configure is clicked for categorical data', async () => {
        const onOpenConfig = vi.fn();
        const panel = useDistributionPanel(() => ({ sources: [categoricalSource()] }));
        render(DatasetDistributionHeader, {
            props: {
                title: 'Distribution',
                panel,
                histogramBinCount: 20,
                ...defaultCallbacks,
                onOpenConfig
            }
        });
        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        expect(onOpenConfig).toHaveBeenCalledOnce();
    });

    it('shows an inline updating banner when stale buckets are present and loading', () => {
        // Non-empty buckets → CategoricalStatusBanner shows "Updating values…" inline.
        renderHeader([categoricalSource({ loading: true })]);
        expect(screen.getByRole('status')).toHaveTextContent('Updating values');
    });

    it('shows an inline error banner when stale buckets are present and there is an error', () => {
        // Non-empty buckets + error → CategoricalStatusBanner shows "Could not update" inline.
        // The chart remains visible in DatasetDistributionContent (not rendered here).
        renderHeader([categoricalSource({ error: 'network failure' })]);
        expect(screen.getByRole('alert')).toHaveTextContent('Could not update');
    });
});
