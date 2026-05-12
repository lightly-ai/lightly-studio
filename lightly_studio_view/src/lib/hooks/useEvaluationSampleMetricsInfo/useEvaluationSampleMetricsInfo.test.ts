import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useEvaluationSampleMetricsInfo } from './useEvaluationSampleMetricsInfo';
import { getEvaluationSampleMetricsInfo } from '$lib/api/lightly_studio_local/sdk.gen';
import { getEvaluationSampleMetricsInfoOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import * as tanstackQuery from '@tanstack/svelte-query';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getEvaluationSampleMetricsInfo: vi.fn()
}));

describe('useEvaluationSampleMetricsInfo', () => {
    const mockQueryResult = {
        data: [],
        isSuccess: true,
        subscribe: vi.fn()
    } as unknown as CreateQueryResult<EvaluationRunMetricsInfoView[], Error>;

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(mockQueryResult);
    });

    it('creates the query with the correct query key for the given dataset id', () => {
        const datasetId = 'dataset-1';
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useEvaluationSampleMetricsInfo({ datasetId });

        const optionsArg = createQuerySpy.mock.calls[0][0] as CreateQueryOptions;
        const expectedOptions = getEvaluationSampleMetricsInfoOptions({
            path: { dataset_id: datasetId }
        });

        expect(optionsArg.queryKey).toEqual(expectedOptions.queryKey);
    });

    it('calls the SDK function with the correct dataset id', async () => {
        const datasetId = 'dataset-2';
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        vi.mocked(getEvaluationSampleMetricsInfo).mockResolvedValue(
            [] as unknown as Awaited<ReturnType<typeof getEvaluationSampleMetricsInfo>>
        );

        useEvaluationSampleMetricsInfo({ datasetId });

        const optionsArg = createQuerySpy.mock.calls[0][0] as CreateQueryOptions;

        await (
            optionsArg.queryFn as (ctx: {
                queryKey: unknown;
                signal: AbortSignal;
            }) => Promise<unknown>
        )({
            queryKey: optionsArg.queryKey,
            signal: new AbortController().signal
        });

        expect(getEvaluationSampleMetricsInfo).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { dataset_id: datasetId },
                throwOnError: true,
                signal: expect.any(AbortSignal)
            })
        );
    });

    it('returns the result of createQuery', () => {
        const result = useEvaluationSampleMetricsInfo({ datasetId: 'dataset-3' });

        expect(result).toMatchObject({ data: [], isSuccess: true });
    });
});
