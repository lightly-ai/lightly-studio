import { getAdjacentSamples } from '$lib/api/lightly_studio_local/sdk.gen';
import { getAdjacentSamplesOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useAdjacentSamples } from './useAdjacentSamples';
import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

const waitForSuccess = async <T>(store: { subscribe: (cb: (value: T) => void) => () => void }) =>
    new Promise<T>((resolve) => {
        const unsubscribe = store.subscribe((value) => {
            // @ts-expect-error tanstack query result shape
            if (value.isSuccess) {
                // @ts-expect-error tanstack query result shape
                resolve(value.data);
                unsubscribe();
            }
        });
    });

describe('useAdjacentSamples', () => {
    let queryClient: QueryClient;

    beforeEach(() => {
        vi.resetAllMocks();
        queryClient = new QueryClient();
    });

    it('runs the query produced by getAdjacentSamplesOptions', async () => {
        vi.mocked(getAdjacentSamples).mockResolvedValue({
            data: buildResponse()
        });

        const params = {
            sampleId: 'sample-1',
            body: { sample_type: 'video', filters: { sample_filter: { collection_id: 'col-1' } } }
        };

        const { query } = useAdjacentSamples({ params, queryClient });
        const result = await waitForSuccess(query);

        expect(result).toEqual(buildResponse());
        expect(getAdjacentSamples).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { sample_id: 'sample-1' },
                body: params.body,
                throwOnError: true
            })
        );
    });

    it('invalidates the hook query key when refetch is called', async () => {
        vi.mocked(getAdjacentSamples).mockResolvedValue({
            data: buildResponse({ current_sample_position: 3 })
        });

        const params = {
            sampleId: 'sample-2',
            body: { sample_type: 'image', filters: { sample_filter: { collection_id: 'col-2' } } }
        };

        const expectedOptions = getAdjacentSamplesOptions({
            path: { sample_id: params.sampleId },
            body: params.body
        });

        const { query, refetch } = useAdjacentSamples({ params, queryClient });
        await waitForSuccess(query);

        const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
        refetch();
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: expectedOptions.queryKey });
    });
});
