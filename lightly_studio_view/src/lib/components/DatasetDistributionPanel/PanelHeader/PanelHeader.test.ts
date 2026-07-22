import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PanelHeader from './PanelHeader.svelte';
import type { DistributionConfig } from '../types';

const config: DistributionConfig = {
    mode: 'topN',
    n: 5,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'vertical'
};

const defaultProps = {
    config,
    classCount: 5,
    visibleClassCount: 5,
    totalCount: 491,
    onConfigure: vi.fn()
};

describe('PanelHeader', () => {
    it('uses the singular noun for a single class', () => {
        render(PanelHeader, { props: { ...defaultProps, classCount: 1, visibleClassCount: 1 } });

        expect(screen.getByText(/^1 class ·/)).toBeInTheDocument();
    });

    it('reflects the active sort option and formats large totals', () => {
        render(PanelHeader, {
            props: {
                ...defaultProps,
                config: { ...config, sortBy: 'name' },
                totalCount: 12345
            }
        });

        expect(screen.getByText(/sorted by class name · 12,345 annotations/)).toBeInTheDocument();
    });

    it('uses a custom value noun', () => {
        render(PanelHeader, { props: { ...defaultProps, valueNoun: 'samples' } });

        expect(screen.getByText(/491 samples/)).toBeInTheDocument();
    });

    it('shows the "Show all" action only for a visible subset and forwards clicks', async () => {
        const onShowAll = vi.fn();
        render(PanelHeader, {
            props: { ...defaultProps, classCount: 30, visibleClassCount: 10, onShowAll }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-show-all'));

        expect(onShowAll).toHaveBeenCalledOnce();
    });

    it('labels a top-N subset with "Top" and a manual subset with "Showing"', () => {
        const { unmount } = render(PanelHeader, {
            props: { ...defaultProps, classCount: 30, visibleClassCount: 10 }
        });
        expect(screen.getByText(/^Top 10 of 30 classes/)).toBeInTheDocument();
        unmount();

        render(PanelHeader, {
            props: {
                ...defaultProps,
                config: { ...config, mode: 'manual' },
                classCount: 30,
                visibleClassCount: 10
            }
        });
        expect(screen.getByText(/^Showing 10 of 30 classes/)).toBeInTheDocument();
    });

    it('hides the "Show all" action when all classes are visible', () => {
        const onShowAll = vi.fn();
        render(PanelHeader, { props: { ...defaultProps, onShowAll } });

        expect(screen.queryByTestId('dataset-distribution-show-all')).not.toBeInTheDocument();
    });

    it('always renders the configure button and forwards clicks', async () => {
        const onConfigure = vi.fn();
        render(PanelHeader, { props: { ...defaultProps, onConfigure } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));

        expect(onConfigure).toHaveBeenCalledOnce();
    });

    it('renders the orientation toggle only when a handler is provided', async () => {
        const onToggleOrientation = vi.fn();
        const { unmount } = render(PanelHeader, { props: defaultProps });
        expect(
            screen.queryByTestId('dataset-distribution-toggle-orientation')
        ).not.toBeInTheDocument();
        unmount();

        render(PanelHeader, { props: { ...defaultProps, onToggleOrientation } });
        await fireEvent.click(screen.getByTestId('dataset-distribution-toggle-orientation'));

        expect(onToggleOrientation).toHaveBeenCalledOnce();
    });

    it('renders the expand button only when a handler is provided', async () => {
        const onExpand = vi.fn();
        const { unmount } = render(PanelHeader, { props: defaultProps });
        expect(screen.queryByTestId('dataset-distribution-expand')).not.toBeInTheDocument();
        unmount();

        render(PanelHeader, { props: { ...defaultProps, onExpand } });
        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));

        expect(onExpand).toHaveBeenCalledOnce();
    });

    it('applies a custom test-id prefix to its buttons', () => {
        render(PanelHeader, {
            props: { ...defaultProps, testIdPrefix: 'dataset-distribution-expanded' }
        });

        expect(screen.getByTestId('dataset-distribution-expanded-configure')).toBeInTheDocument();
    });
});
