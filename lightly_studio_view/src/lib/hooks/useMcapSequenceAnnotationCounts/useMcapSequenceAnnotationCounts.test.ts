import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import * as svelteQueryGen from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    buildMcapSequenceAnnotationCountsRequest,
    useMcapSequenceAnnotationCounts
} from './useMcapSequenceAnnotationCounts';

describe('buildMcapSequenceAnnotationCountsRequest', () => {
    it('sends the filter for the collection', () => {
        const filter = { filter_type: 'mcap_sequence' as const };

        expect(buildMcapSequenceAnnotationCountsRequest({ collectionId: 'col-1', filter })).toEqual(
            { path: { collection_id: 'col-1' }, body: { filter } }
        );
    });
});

describe('useMcapSequenceAnnotationCounts', () => {
    const baseOptions = { queryKey: ['mcap-sequence-annotation-counts'], queryFn: vi.fn() };
    let queryOptionsThunk: () => {
        enabled: boolean;
        placeholderData: (previousData: unknown) => unknown;
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(svelteQueryGen, 'countMcapSequenceAnnotationsByCollectionOptions').mockReturnValue(
            baseOptions as unknown as ReturnType<
                typeof svelteQueryGen.countMcapSequenceAnnotationsByCollectionOptions
            >
        );
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as typeof queryOptionsThunk;
            return {} as ReturnType<typeof tanstackQuery.createQuery>;
        });
    });

    it('is enabled by default', () => {
        useMcapSequenceAnnotationCounts(() => ({ collectionId: 'col-1' }));

        expect(queryOptionsThunk()).toEqual({
            ...baseOptions,
            placeholderData: expect.any(Function),
            enabled: true
        });
    });

    it('passes enabled through', () => {
        useMcapSequenceAnnotationCounts(() => ({ collectionId: 'col-1', enabled: false }));

        expect(queryOptionsThunk().enabled).toBe(false);
    });

    it('keeps the previous counts while the next request runs', () => {
        useMcapSequenceAnnotationCounts(() => ({ collectionId: 'col-1' }));
        const previousData = [{ label_name: 'car', total_count: 3, current_count: 1 }];

        expect(queryOptionsThunk().placeholderData(previousData)).toBe(previousData);
    });
});
