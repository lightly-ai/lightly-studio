import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as tanstackQuery from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '../useImageAnnotationCounts/useImageAnnotationCounts';
import { useUnannotatedSampleCount } from './useUnannotatedSampleCount';

describe('useUnannotatedSampleCount', () => {
    let queryOptionsThunk: () => { queryKey: unknown[]; enabled: boolean };

    beforeEach(() => {
        vi.spyOn(tanstackQuery, 'createQuery').mockImplementation((thunk) => {
            queryOptionsThunk = thunk as unknown as typeof queryOptionsThunk;
            return {} as ReturnType<typeof tanstackQuery.createQuery>;
        });
    });

    it('keys the image count under the image annotation counts', () => {
        useUnannotatedSampleCount(() => ({ collectionId: 'col-1', sampleType: 'image' }));

        const { queryKey, enabled } = queryOptionsThunk();
        expect(queryKey.slice(0, useImageAnnotationCountsQueryKey.length)).toEqual(
            useImageAnnotationCountsQueryKey
        );
        expect(enabled).toBe(true);
    });

    it('requests the video count for videos', () => {
        const filter = { filter_type: 'video' as const };
        useUnannotatedSampleCount(() => ({
            collectionId: 'col-1',
            sampleType: 'video',
            filter,
            enabled: false
        }));

        const { queryKey, enabled } = queryOptionsThunk();
        expect(queryKey).toEqual([
            expect.objectContaining({
                _id: 'countUnannotatedVideos',
                path: { collection_id: 'col-1' },
                body: { filter }
            })
        ]);
        expect(enabled).toBe(false);
    });
});
