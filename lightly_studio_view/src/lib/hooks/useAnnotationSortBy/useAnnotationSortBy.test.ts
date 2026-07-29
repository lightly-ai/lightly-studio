import { beforeEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import type { AnnotationEvaluationMetricSortExpr } from '$lib/api/lightly_studio_local';
import { useAnnotationSortBy } from './useAnnotationSortBy';

const SORT_BY: AnnotationEvaluationMetricSortExpr = {
    source: 'annotation_evaluation_metric',
    evaluation_run_id: 'run-1',
    metric_name: 'iou',
    direction: 'asc'
};

describe('useAnnotationSortBy', () => {
    beforeEach(() => {
        // The store is module-level, so reset it between tests.
        useAnnotationSortBy().setSortBy('any-source', null);
    });

    it('defaults to no sort', () => {
        const { getSortBy } = useAnnotationSortBy();

        expect(getSortBy('source-1')).toBeNull();
    });

    it('returns the expression set for a source', () => {
        const { setSortBy, getSortBy } = useAnnotationSortBy();

        setSortBy('source-1', SORT_BY);

        expect(getSortBy('source-1')).toEqual(SORT_BY);
    });

    it('resets the sort when the annotation source changes', () => {
        const { setSortBy, getSortBy } = useAnnotationSortBy();
        setSortBy('source-1', SORT_BY);

        expect(getSortBy('source-2')).toBeNull();
    });

    it('clears the sort when set to null', () => {
        const { setSortBy, getSortBy } = useAnnotationSortBy();
        setSortBy('source-1', SORT_BY);

        setSortBy('source-1', null);

        expect(getSortBy('source-1')).toBeNull();
    });

    it('exposes the selection reactively through sortByFor', () => {
        const { setSortBy, sortByFor } = useAnnotationSortBy();

        setSortBy('source-1', SORT_BY);

        expect(get(sortByFor)('source-1')).toEqual(SORT_BY);
        expect(get(sortByFor)('source-2')).toBeNull();
    });
});
