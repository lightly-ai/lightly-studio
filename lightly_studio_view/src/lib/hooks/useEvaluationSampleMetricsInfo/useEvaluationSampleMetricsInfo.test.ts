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
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useEvaluationSampleMetricsInfo({ datasetId: () => 'dataset-1' });

        const optionsArg = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        const expectedOptions = getEvaluationSampleMetricsInfoOptions({
            path: { dataset_id: 'dataset-1' }
        });

        expect(optionsArg.queryKey).toEqual(expectedOptions.queryKey);
    });

    it('reacts to datasetId getter changes — query key switches to the new id', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        let datasetId = 'ds1';
        useEvaluationSampleMetricsInfo({ datasetId: () => datasetId });

        const optionsFn = createQuerySpy.mock.calls[0][0] as () => CreateQueryOptions;

        expect(optionsFn().queryKey).toEqual(
            getEvaluationSampleMetricsInfoOptions({ path: { dataset_id: 'ds1' } }).queryKey
        );

        datasetId = 'ds2';

        expect(optionsFn().queryKey).toEqual(
            getEvaluationSampleMetricsInfoOptions({ path: { dataset_id: 'ds2' } }).queryKey
        );
    });

    it('calls the SDK function with the correct dataset id', async () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        vi.mocked(getEvaluationSampleMetricsInfo).mockResolvedValue(
            [] as unknown as Awaited<ReturnType<typeof getEvaluationSampleMetricsInfo>>
        );

        useEvaluationSampleMetricsInfo({ datasetId: () => 'dataset-2' });

        const optionsArg = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;

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
                path: { dataset_id: 'dataset-2' },
                throwOnError: true,
                signal: expect.any(AbortSignal)
            })
        );
    });

    it('returns the result of createQuery', () => {
        const result = useEvaluationSampleMetricsInfo({ datasetId: () => 'dataset-3' });

        expect(result).toMatchObject({ data: [], isSuccess: true });
    });
});
