import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import AnnotationDetailsNavigation from './AnnotationDetailsNavigation.svelte';

const COLLECTION_ID = 'source-1';
const DATASET_ID = 'dataset-1';
// The dataset segment of the URL is the root collection ID, which the runs endpoint cannot resolve.
const ROUTE_DATASET_ID = 'root-collection-1';

const defaultProps = { collectionDatasetId: DATASET_ID };

const mocks = vi.hoisted(() => ({
    runsProxy: { data: [] as unknown[] },
    runsParams: [] as { datasetId: string }[],
    adjacentProxy: {
        data: { previous_sample_id: 'annotation-0', next_sample_id: 'annotation-2' } as
            | { previous_sample_id: string | null; next_sample_id: string | null }
            | undefined
    }
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// The IDs are inlined below: `vi.mock` factories are hoisted above the constants.
vi.mock('$app/state', () => ({
    page: {
        params: {
            collection_id: 'source-1',
            dataset_id: 'root-collection-1',
            collection_type: 'annotation',
            annotationId: 'annotation-1'
        }
    }
}));

// Mocked at the source modules rather than at the `$lib/hooks` barrel, so both the component and
// the hook it uses see the mocks when importing through the barrel.
vi.mock('$lib/hooks/useAdjacentAnnotations/useAdjacentAnnotations', () => ({
    useAdjacentAnnotations: () => ({ query: mocks.adjacentProxy })
}));

vi.mock('$lib/hooks/useEvaluationRuns/useEvaluationRuns', () => ({
    useEvaluationRuns: (getParams: () => { datasetId: string }) => {
        mocks.runsParams.push(getParams());
        return mocks.runsProxy;
    },
    useInvalidateEvaluationRunsQueries: () => vi.fn()
}));

const STALE_RUN = {
    id: 'run-1',
    name: 'detection eval',
    stale_since: new Date('2026-01-01')
} as EvaluationRunView;

const FRESH_RUN = { ...STALE_RUN, stale_since: null } as EvaluationRunView;

const IOU_SORT = {
    source: 'annotation_evaluation_metric',
    evaluation_run_id: 'run-1',
    metric_name: 'iou',
    direction: 'asc'
} as const;

describe('AnnotationDetailsNavigation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.runsProxy.data = [STALE_RUN];
        mocks.runsParams = [];
        useAnnotationSortBy().setSortBy(COLLECTION_ID, null);
    });

    it('warns without offering a recompute when the run the order follows is stale', () => {
        useAnnotationSortBy().setSortBy(COLLECTION_ID, IOU_SORT);
        render(AnnotationDetailsNavigation, { props: defaultProps });

        expect(screen.getByTestId('annotation-navigation-stale-icon')).toBeInTheDocument();
        expect(screen.getByLabelText(/go back to the grid view to recompute/i)).toBeInTheDocument();
        expect(screen.queryByTestId('annotation-sort-recompute-button')).not.toBeInTheDocument();
        expect(screen.getByTestId('annotation-navigation')).toBeInTheDocument();
        // The warning is positioned against the image area, so it must not sit inside the
        // navigation wrapper.
        expect(
            screen
                .getByTestId('annotation-navigation')
                .querySelector('[data-testid="annotation-navigation-stale-icon"]')
        ).toBeNull();
    });

    it('shows no warning when the run the order follows is up to date', () => {
        mocks.runsProxy.data = [FRESH_RUN];
        useAnnotationSortBy().setSortBy(COLLECTION_ID, IOU_SORT);
        render(AnnotationDetailsNavigation, { props: defaultProps });

        expect(screen.queryByTestId('annotation-navigation-stale-icon')).not.toBeInTheDocument();
    });

    it('looks up the runs of the dataset, not of the root collection in the URL', () => {
        render(AnnotationDetailsNavigation, { props: defaultProps });

        expect(mocks.runsParams).toContainEqual({ datasetId: DATASET_ID });
        expect(mocks.runsParams).not.toContainEqual({ datasetId: ROUTE_DATASET_ID });
    });

    it('shows no warning while no sort is active, even with a stale run', () => {
        render(AnnotationDetailsNavigation, { props: defaultProps });

        expect(screen.queryByTestId('annotation-navigation-stale-icon')).not.toBeInTheDocument();
    });
});
