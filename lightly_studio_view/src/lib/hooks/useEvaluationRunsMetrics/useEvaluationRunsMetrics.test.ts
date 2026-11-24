import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getEvaluationRunsMetricsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { EvaluationRunMetricsView } from '$lib/api/lightly_studio_local';
import { useEvaluationRunsMetrics } from './useEvaluationRunsMetrics';

describe('useEvaluationRunsMetrics', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue({
            data: []
        } as unknown as CreateQueryResult<EvaluationRunMetricsView[], Error>);
    });

    it('queries the metrics of the given runs', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useEvaluationRunsMetrics(() => ({
            datasetId: 'dataset-1',
            runIds: ['run-1', 'run-2'],
            tagIds: ['tag-1']
        }));

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(
            getEvaluationRunsMetricsOptions({
                path: { dataset_id: 'dataset-1' },
                query: { run_ids: ['run-1', 'run-2'], tag_ids: ['tag-1'] }
            }).queryKey
        );
        expect(options.enabled).toBe(true);
        // Changing the tags keeps the page on screen while the new slices load.
        expect(options.placeholderData).toBe(tanstackQuery.keepPreviousData);
    });

    it('disables the query when enabled is false', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useEvaluationRunsMetrics(() => ({
            datasetId: 'dataset-1',
            runIds: [],
            tagIds: [],
            enabled: false
        }));

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.enabled).toBe(false);
    });
});
