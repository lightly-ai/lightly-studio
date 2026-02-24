import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAdjacentSamples } from './useAdjacentSamples';
import { getAdjacentSamples } from '$lib/api/lightly_studio_local/sdk.gen';
import { getAdjacentSamplesOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { CreateQueryResult, QueryClient } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getAdjacentSamples: vi.fn()
}));

const buildResponse = (
    overrides: Partial<Awaited<ReturnType<typeof getAdjacentSamples>>['data']> = {}
) => ({
    previous_sample_id: 'prev',
    sample_id: 'current',
    next_sample_id: 'next',
    current_sample_position: 5,
    total_count: 10,
    ...overrides
});

describe('useAdjacentSamples', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    const mockQueryResult: CreateQueryResult<AdjacentData, Error> = {
        data: buildResponse(),
        isSuccess: true,
        refetch: vi.fn(),
        subscribe: vi.fn()
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue({
            ...mockQueryResult,
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryResult);
                return vi.fn();
            }
        });
    });

    it('creates the query with adjacent sample options', async () => {
        vi.mocked(getAdjacentSamples).mockResolvedValue({ data: buildResponse() });

        const params = {
            sampleId: 'sample-1',
            body: { sample_type: 'video', filters: { sample_filter: { collection_id: 'col-1' } } }
        };

        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useAdjacentSamples({ params });

        const optionsArg = createQuerySpy.mock.calls[0][0];
        const expectedOptions = getAdjacentSamplesOptions({
            path: { sample_id: params.sampleId },
            body: params.body
        });

        expect(optionsArg.queryKey).toEqual(expectedOptions.queryKey);

        await optionsArg.queryFn({
            queryKey: optionsArg.queryKey,
            signal: new AbortController().signal
        });

        expect(getAdjacentSamples).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { sample_id: 'sample-1' },
                body: params.body,
                throwOnError: true,
                signal: expect.any(AbortSignal)
            })
        );
    });

    it('invalidates the hook query key when refetch is called', () => {
        const params = {
            sampleId: 'sample-2',
            body: { sample_type: 'image', filters: { sample_filter: { collection_id: 'col-2' } } }
        };

        const expectedOptions = getAdjacentSamplesOptions({
            path: { sample_id: params.sampleId },
            body: params.body
        });

        const { refetch } = useAdjacentSamples({ params });

        refetch();

        expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: expectedOptions.queryKey });
    });
});
