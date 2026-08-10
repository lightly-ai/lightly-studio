import { describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import {
    getAnnotationGridQueryKeyPrefixes,
    useInvalidateAnnotationGridQueries
} from './useInvalidateAnnotationGridQueries';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: vi.fn() }));

describe('useInvalidateAnnotationGridQueries', () => {
    it('builds the image, frame, and annotation grid query-key prefixes', () => {
        expect(getAnnotationGridQueryKeyPrefixes('col-1')).toEqual([
            ['readImagesInfinite', 'col-1'],
            [
                {
                    _id: 'getAllFrames',
                    _infinite: true,
                    path: { video_frame_collection_id: 'col-1' }
                }
            ],
            ['readAnnotationsWithPayloadInfinite', 'col-1']
        ]);
    });

    it('invalidates every annotation-bearing grid prefix', () => {
        const invalidateQueries = vi.fn();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);

        useInvalidateAnnotationGridQueries()('col-1');

        expect(invalidateQueries.mock.calls).toEqual(
            getAnnotationGridQueryKeyPrefixes('col-1').map((queryKey) => [{ queryKey }])
        );
    });
});
