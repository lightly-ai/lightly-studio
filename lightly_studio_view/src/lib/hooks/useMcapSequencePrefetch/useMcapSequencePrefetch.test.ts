import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as queryOptions from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useMcapSequencePrefetch } from './useMcapSequencePrefetch';

describe('useMcapSequencePrefetch', () => {
    const prefetchQuery = vi.fn();
    const cancelQueries = vi.fn();
    const summaryOptions = { queryKey: ['summary'] } as unknown as ReturnType<
        typeof queryOptions.getSummaryOptions
    >;
    const ticksOptions = { queryKey: ['ticks'] } as unknown as ReturnType<
        typeof queryOptions.getTicksOptions
    >;

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue({
            prefetchQuery,
            cancelQueries
        } as unknown as QueryClient);
        vi.spyOn(queryOptions, 'getSummaryOptions').mockReturnValue(summaryOptions);
        vi.spyOn(queryOptions, 'getTicksOptions').mockReturnValue(ticksOptions);
    });

    it('prefetches only the selected sequence metadata', () => {
        const { prefetch } = useMcapSequencePrefetch(() => 'dataset-1');

        prefetch('sequence-1');

        expect(prefetchQuery).toHaveBeenCalledTimes(2);
        expect(queryOptions.getSummaryOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' }
        });
        expect(queryOptions.getTicksOptions).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' }
        });
    });

    it('cancels the selected sequence metadata when hover ends', () => {
        const { cancel } = useMcapSequencePrefetch(() => 'dataset-1');

        cancel('sequence-1');

        expect(cancelQueries).toHaveBeenCalledWith({ queryKey: ['summary'], exact: true });
        expect(cancelQueries).toHaveBeenCalledWith({ queryKey: ['ticks'], exact: true });
    });

    it('does nothing until the dataset is available', () => {
        const { prefetch, cancel } = useMcapSequencePrefetch(() => '');

        prefetch('sequence-1');
        cancel('sequence-1');

        expect(prefetchQuery).not.toHaveBeenCalled();
        expect(cancelQueries).not.toHaveBeenCalled();
    });
});
