import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { readable } from 'svelte/store';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EvaluationRunAnnotationMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import AnnotationOrderBy from './AnnotationOrderBy.svelte';

const RUN: EvaluationRunAnnotationMetricsInfoView = {
    run_id: 'run-1',
    run_name: 'detection eval',
    task_type: 'object_detection',
    metric_names: ['iou']
};

const mocks = vi.hoisted(() => ({
    trackEvent: vi.fn(),
    metricsProxy: { data: null as unknown[] | null, dataUpdatedAt: 0 },
    textEmbeddingValue: undefined as TextEmbedding | undefined
}));

vi.mock('$lib/hooks', () => ({
    usePostHog: () => ({ trackEvent: mocks.trackEvent }),
    useGlobalStorage: () => ({ textEmbedding: readable(mocks.textEmbeddingValue) })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ textEmbedding: readable(mocks.textEmbeddingValue) })
}));

vi.mock('$lib/hooks/useAnnotationEvaluationMetricsInfo/useAnnotationEvaluationMetricsInfo', () => ({
    useAnnotationEvaluationMetricsInfo: () => mocks.metricsProxy
}));

const COLLECTION_ID = 'source-1';

describe('AnnotationOrderBy', () => {
    beforeAll(() => {
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
        Element.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
        vi.clearAllMocks();
        mocks.metricsProxy.data = [RUN];
        mocks.metricsProxy.dataUpdatedAt = 0;
        mocks.textEmbeddingValue = undefined;
        useAnnotationSortBy().setSortBy(COLLECTION_ID, null);
    });

    it('renders with a Default entry and one entry per run and metric', async () => {
        const user = userEvent.setup();
        render(AnnotationOrderBy, { props: { collectionId: COLLECTION_ID } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-default')).toHaveTextContent('Default');
        expect(screen.getByTestId('sort-field-run-1-iou')).toHaveTextContent('detection eval.iou');
    });

    it('renders when the source has no evaluation runs', async () => {
        const user = userEvent.setup();
        mocks.metricsProxy.data = [];
        render(AnnotationOrderBy, { props: { collectionId: COLLECTION_ID } });

        await user.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-default')).toBeInTheDocument();
    });

    it('produces the annotation sort expression for the picked option', async () => {
        const user = userEvent.setup();
        render(AnnotationOrderBy, { props: { collectionId: COLLECTION_ID } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-run-1-iou'));

        expect(useAnnotationSortBy().getSortBy(COLLECTION_ID)).toEqual({
            source: 'annotation_evaluation_metric',
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'asc'
        });
    });

    it('clears the sort when picking Default', async () => {
        const user = userEvent.setup();
        useAnnotationSortBy().setSortBy(COLLECTION_ID, {
            source: 'annotation_evaluation_metric',
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'asc'
        });
        render(AnnotationOrderBy, { props: { collectionId: COLLECTION_ID } });

        await user.click(screen.getByTestId('sort-by-trigger'));
        await user.click(screen.getByTestId('sort-field-default'));

        expect(useAnnotationSortBy().getSortBy(COLLECTION_ID)).toBeNull();
    });

    it('is disabled during similarity search', () => {
        mocks.textEmbeddingValue = { queryText: 'cat', embedding: [0.1] } as TextEmbedding;
        render(AnnotationOrderBy, { props: { collectionId: COLLECTION_ID } });

        expect(screen.getByTestId('sort-by-trigger')).toBeDisabled();
        expect(screen.getByTestId('sort-direction-button')).toBeDisabled();
    });
});
