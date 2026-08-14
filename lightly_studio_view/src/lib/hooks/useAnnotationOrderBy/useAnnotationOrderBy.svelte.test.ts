import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { get } from 'svelte/store';
import type { EvaluationRunAnnotationMetricsInfoView } from '$lib/api/lightly_studio_local';
import { useAnnotationSortBy } from '$lib/hooks/useAnnotationSortBy/useAnnotationSortBy';
import { mapRunsToAnnotationSortFields, useAnnotationOrderBy } from './useAnnotationOrderBy.svelte';

const RUN: EvaluationRunAnnotationMetricsInfoView = {
    run_id: 'run-1',
    run_name: 'detection eval',
    task_type: 'object_detection',
    metrics: [{ metric_name: 'iou' }]
};

const { trackEventMock, metricsInfo } = vi.hoisted(() => ({
    trackEventMock: vi.fn(),
    metricsInfo: { data: [] as unknown[], dataUpdatedAt: 0 }
}));

vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    usePostHog: () => ({ trackEvent: trackEventMock }),
    useAnnotationEvaluationMetricsInfo: () => metricsInfo
}));

const COLLECTION_ID = 'source-1';

describe('useAnnotationOrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        metricsInfo.data = [RUN];
        useAnnotationSortBy().setSortBy(COLLECTION_ID, null);
    });

    it('selects a field as an ascending annotation sort expression', () => {
        const { handleFieldClick, dispose } = useAnnotationOrderBy({
            collectionId: () => COLLECTION_ID
        });

        handleFieldClick(mapRunsToAnnotationSortFields([RUN])[0]);

        expect(useAnnotationSortBy().getSortBy(COLLECTION_ID)).toEqual({
            source: 'annotation_evaluation_metric',
            evaluation_run_id: 'run-1',
            metric_name: 'iou',
            direction: 'asc'
        });
        dispose();
    });

    it('toggles the direction of the active sort', () => {
        const { handleFieldClick, toggleDirection, selectedDirection, dispose } =
            useAnnotationOrderBy({ collectionId: () => COLLECTION_ID });
        handleFieldClick(mapRunsToAnnotationSortFields([RUN])[0]);

        toggleDirection();

        expect(useAnnotationSortBy().getSortBy(COLLECTION_ID)?.direction).toBe('desc');
        expect(get(selectedDirection)).toBe('desc');
        dispose();
    });

    it('clears the sort when the active field is picked again', () => {
        const { handleFieldClick, dispose } = useAnnotationOrderBy({
            collectionId: () => COLLECTION_ID
        });
        const field = mapRunsToAnnotationSortFields([RUN])[0];
        handleFieldClick(field);

        handleFieldClick(field);

        expect(useAnnotationSortBy().getSortBy(COLLECTION_ID)).toBeNull();
        dispose();
    });

    it('drops the selection when the browsed annotation source changes', () => {
        let collectionId = $state(COLLECTION_ID);
        const { handleFieldClick, selectedIndex, dispose } = useAnnotationOrderBy({
            collectionId: () => collectionId
        });
        // Subscribed, like a rendered control: a stale selection would not be recomputed on read.
        let index = -1;
        const unsubscribe = selectedIndex.subscribe((value) => (index = value));
        flushSync();
        handleFieldClick(mapRunsToAnnotationSortFields([RUN])[0]);
        expect(index).toBe(0);

        collectionId = 'source-2';
        flushSync();

        expect(index).toBe(-1);
        unsubscribe();
        dispose();
    });

    it('emits the same analytics event as image sorting', () => {
        const { handleFieldClick, dispose } = useAnnotationOrderBy({
            collectionId: () => COLLECTION_ID
        });
        flushSync();

        handleFieldClick(mapRunsToAnnotationSortFields([RUN])[0]);

        expect(trackEventMock).toHaveBeenCalledWith('grid_sorted', {
            collection_id: COLLECTION_ID,
            sort_source: 'annotation_evaluation_metric',
            field_name: 'detection eval.iou',
            direction: 'asc'
        });
        dispose();
    });
});

describe('mapRunsToAnnotationSortFields', () => {
    it('names both the run and the metric, one entry per pair', () => {
        const fields = mapRunsToAnnotationSortFields([
            { ...RUN, metrics: [{ metric_name: 'iou' }, { metric_name: 'disagreement' }] }
        ]);

        expect(fields).toEqual([
            {
                source: 'annotation_evaluation_metric',
                evaluation_run_id: 'run-1',
                metric_name: 'iou',
                label: 'detection eval.iou'
            },
            {
                source: 'annotation_evaluation_metric',
                evaluation_run_id: 'run-1',
                metric_name: 'disagreement',
                label: 'detection eval.disagreement'
            }
        ]);
    });
});
