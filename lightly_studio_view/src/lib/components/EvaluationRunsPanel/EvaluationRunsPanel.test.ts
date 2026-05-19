import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import EvaluationRunsPanel from './EvaluationRunsPanel.svelte';

const noop = () => {};

type Props = {
    onClose: () => void;
    evaluationRuns: EvaluationRunView[];
    isLoading: boolean;
    error?: string;
};

const renderPanel = (overrides: Partial<Props> = {}) =>
    render(EvaluationRunsPanel, {
        props: {
            onClose: noop,
            evaluationRuns: [],
            isLoading: false,
            ...overrides
        }
    });

describe('EvaluationRunsPanel', () => {
    it('renders a spinner while loading', () => {
        const { container } = renderPanel({ isLoading: true });

        expect(container.querySelector('.animate-spin')).toBeInTheDocument();
        expect(screen.queryByTestId('evaluation-runs-list')).not.toBeInTheDocument();
        expect(screen.queryByTestId('evaluation-runs-empty')).not.toBeInTheDocument();
    });

    it('renders an error message when error is set', () => {
        renderPanel({ error: 'boom' });

        expect(screen.getByText(/Error loading evaluation runs: boom/)).toBeInTheDocument();
    });

    it('renders the empty state when there are no runs', () => {
        renderPanel({ evaluationRuns: [] });

        expect(screen.getByTestId('evaluation-runs-empty')).toBeInTheDocument();
        expect(screen.getByText('No evaluation runs yet')).toBeInTheDocument();
        expect(screen.queryByTestId('evaluation-runs-list')).not.toBeInTheDocument();
    });

    it('renders one item per run', () => {
        const runs: EvaluationRunView[] = [
            {
                id: 'run-a',
                name: 'Run A',
                evaluation_run_configuration: {},
                created_at: new Date('2026-01-01T00:00:00Z')
            },
            {
                id: 'run-b',
                name: 'Run B',
                evaluation_run_configuration: {},
                created_at: new Date('2026-02-01T00:00:00Z')
            }
        ];
        renderPanel({ evaluationRuns: runs });

        const items = screen.getAllByTestId('evaluation-run-item');
        expect(items).toHaveLength(2);
        expect(screen.getByText('Run A')).toBeInTheDocument();
        expect(screen.getByText('Run B')).toBeInTheDocument();
    });

    it('expands only the clicked run and collapses it on a second click', async () => {
        const runs: EvaluationRunView[] = [
            {
                id: 'run-a',
                name: 'Run A',
                evaluation_run_configuration: { iou_threshold: 0.5 },
                created_at: new Date('2026-01-01T00:00:00Z')
            },
            {
                id: 'run-b',
                name: 'Run B',
                evaluation_run_configuration: { iou_threshold: 0.75 },
                created_at: new Date('2026-02-01T00:00:00Z')
            }
        ];
        renderPanel({ evaluationRuns: runs });

        const [itemA, itemB] = screen.getAllByTestId('evaluation-run-item');

        await fireEvent.click(itemA);
        let details = screen.getAllByTestId('evaluation-run-details');
        expect(details).toHaveLength(1);
        expect(itemA).toHaveAttribute('aria-expanded', 'true');
        expect(itemB).toHaveAttribute('aria-expanded', 'false');

        await fireEvent.click(itemB);
        details = screen.getAllByTestId('evaluation-run-details');
        expect(details).toHaveLength(1);
        expect(itemA).toHaveAttribute('aria-expanded', 'false');
        expect(itemB).toHaveAttribute('aria-expanded', 'true');

        await fireEvent.click(itemB);
        expect(screen.queryByTestId('evaluation-run-details')).not.toBeInTheDocument();
        expect(itemB).toHaveAttribute('aria-expanded', 'false');
    });

    it('invokes onClose when the close button is clicked', async () => {
        const onClose = vi.fn();
        renderPanel({ onClose });

        await fireEvent.click(screen.getByTestId('evaluation-runs-close-button'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
