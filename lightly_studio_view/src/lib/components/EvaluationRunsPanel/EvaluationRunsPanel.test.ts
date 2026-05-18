import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import EvaluationRunsPanel from './EvaluationRunsPanel.svelte';

const DATASET_ID = 'real-dataset-uuid';

const mockSetShowEvaluationRuns = vi.fn();

vi.mock('$app/state', () => ({
    page: {
        data: { collection: { dataset_id: 'real-dataset-uuid' } }
    }
}));

vi.mock('$lib/hooks/useEvaluationRuns/useEvaluationRuns');

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        setShowEvaluationRuns: mockSetShowEvaluationRuns
    })
}));

type QueryShape = {
    data: EvaluationRunView[] | undefined;
    isLoading: boolean;
    isError: boolean;
    error: Error | null;
};

const mockQuery = (state: Partial<QueryShape>) => {
    const full: QueryShape = {
        data: undefined,
        isLoading: false,
        isError: false,
        error: null,
        ...state
    };
    // Component reads via $derived(useEvaluationRuns(...)) then $store-derefs.
    // Wrapping in a store-shaped object mirrors what createQuery returns.
    const store = {
        subscribe: (run: (value: QueryShape) => void) => {
            run(full);
            return () => {};
        }
    };
    vi.mocked(useEvaluationRuns).mockReturnValue(
        store as unknown as ReturnType<typeof useEvaluationRuns>
    );
};

describe('EvaluationRunsPanel', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('passes the real dataset_id from page.data.collection to the hook', () => {
        mockQuery({ data: [] });
        render(EvaluationRunsPanel);
        expect(useEvaluationRuns).toHaveBeenCalledWith({ datasetId: DATASET_ID });
    });

    it('renders a spinner while loading', () => {
        mockQuery({ isLoading: true });
        const { container } = render(EvaluationRunsPanel);

        expect(container.querySelector('.animate-spin')).toBeInTheDocument();
        expect(screen.queryByTestId('evaluation-runs-list')).not.toBeInTheDocument();
        expect(screen.queryByTestId('evaluation-runs-empty')).not.toBeInTheDocument();
    });

    it('renders an error message when the query fails', () => {
        mockQuery({ isError: true, error: new Error('boom') });
        render(EvaluationRunsPanel);

        expect(screen.getByText(/Error loading evaluation runs: boom/)).toBeInTheDocument();
    });

    it('renders the empty state when there are no runs', () => {
        mockQuery({ data: [] });
        render(EvaluationRunsPanel);

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
        mockQuery({ data: runs });
        render(EvaluationRunsPanel);

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
        mockQuery({ data: runs });
        render(EvaluationRunsPanel);

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

    it('closes the panel when the close button is clicked', async () => {
        mockQuery({ data: [] });
        render(EvaluationRunsPanel);

        await fireEvent.click(screen.getByTestId('evaluation-runs-close-button'));
        expect(mockSetShowEvaluationRuns).toHaveBeenCalledWith(false);
    });
});
