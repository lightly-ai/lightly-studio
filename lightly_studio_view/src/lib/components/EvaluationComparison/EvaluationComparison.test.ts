import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '$lib/api/ApiError';
import type { EvaluationRunMetricsView, EvaluationRunView } from '$lib/api/lightly_studio_local';
import EvaluationComparison from './EvaluationComparison.svelte';
import { makeMetricsView, makeRun } from './fixtures';

const state = vi.hoisted(() => ({
    runs: [] as EvaluationRunView[] | undefined,
    runsError: null as Error | null,
    metrics: undefined as EvaluationRunMetricsView[] | undefined,
    metricsError: null as Error | null,
    metricsEnabled: undefined as boolean | undefined,
    metricsTagIds: undefined as string[] | undefined,
    tags: [{ tag_id: 'tag-1', name: 'night' }]
}));

vi.mock('$lib/hooks', async () => {
    const { readable } = await import('svelte/store');
    return {
        useEvaluationRuns: () => ({
            get data() {
                return state.runs;
            },
            isLoading: false,
            get error() {
                return state.runsError;
            }
        }),
        useTags: () => ({ tags: readable(state.tags) }),
        useEvaluationRunsMetrics: (getParams: () => { enabled?: boolean; tagIds: string[] }) => {
            state.metricsEnabled = getParams().enabled;
            state.metricsTagIds = getParams().tagIds;
            return {
                get data() {
                    return state.metrics;
                },
                get error() {
                    return state.metricsError;
                },
                isLoading: false
            };
        }
    };
});

const defaultProps = {
    datasetId: 'dataset-1',
    collectionId: 'collection-1',
    runIds: ['run-a', 'run-b'],
    tagIds: ['tag-1'],
    onTagIdsChange: vi.fn(),
    imagesHref: '/datasets/dataset-1/image/collection-1/images'
};

describe('EvaluationComparison', () => {
    beforeEach(() => {
        state.runs = [
            makeRun({ id: 'run-a', name: 'run a' }),
            makeRun({ id: 'run-b', name: 'run b' })
        ];
        state.metrics = [makeMetricsView('run-a'), makeMetricsView('run-b')];
        state.metricsError = null;
        state.runsError = null;
    });

    it('ignores tags of the link that do not exist', () => {
        render(EvaluationComparison, {
            props: { ...defaultProps, tagIds: ['tag-1', 'deleted-tag'] }
        });

        expect(state.metricsTagIds).toEqual(['tag-1']);
    });

    it('shows the error when the runs request fails', () => {
        state.runs = undefined;
        state.runsError = new Error('Network down');

        render(EvaluationComparison, { props: defaultProps });

        expect(screen.getByText('Network down')).toBeInTheDocument();
    });

    it('asks for two runs when the link has one', () => {
        render(EvaluationComparison, { props: { ...defaultProps, runIds: ['run-a'] } });

        expect(
            screen.getByText('Select at least two evaluation runs to compare.')
        ).toBeInTheDocument();
        expect(state.metricsEnabled).toBe(false);
    });

    it('asks for runs of the same task type', () => {
        state.runs = [
            makeRun({ id: 'run-a', name: 'run a' }),
            makeRun({ id: 'run-b', task_type: 'classification' })
        ];

        render(EvaluationComparison, { props: defaultProps });

        expect(screen.getByText('Select runs of the same task type.')).toBeInTheDocument();
    });

    it('reports an unknown run with a link back to the images', () => {
        render(EvaluationComparison, { props: { ...defaultProps, runIds: ['run-a', 'deleted'] } });

        expect(screen.getByText('Evaluation run not found.')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Back to images' })).toHaveAttribute(
            'href',
            defaultProps.imagesHref
        );
    });

    it('reports a run that the metrics request does not find', () => {
        state.metrics = undefined;
        state.metricsError = new ApiError('Evaluation run run-b not found.', 404);

        render(EvaluationComparison, { props: defaultProps });

        expect(screen.getByText('Evaluation run not found.')).toBeInTheDocument();
    });

    it('shows the leaderboard of the runs', () => {
        render(EvaluationComparison, { props: defaultProps });

        expect(state.metricsTagIds).toEqual(['tag-1']);

        expect(screen.getByTestId('evaluation-leaderboard')).toHaveTextContent('run a');
        expect(screen.getByTestId('evaluation-leaderboard')).toHaveTextContent('run b');
    });
});
