import { describe, expect, test, vi } from 'vitest';

import { createQuerySelection, createThumbnailUrlResolver } from './tooltipThumbnail';
import { HIDDEN_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

vi.mock('$env/static/public', () => ({
    PUBLIC_SAMPLES_URL: 'https://example.com/images',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: 'https://example.com/frames'
}));

const getVideoById = vi.hoisted(() => vi.fn());
const getAnnotation = vi.hoisted(() => vi.fn());
vi.mock('$lib/api/lightly_studio_local', () => ({ getVideoById, getAnnotation }));

describe('createQuerySelection', () => {
    const params = {
        x: new Float32Array([0, 10]),
        y: new Float32Array([0, 10]),
        sampleIds: ['sample-a', 'sample-b'],
        category: new Uint8Array([INCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY])
    };

    test('returns the nearest point with its sample ID as identifier', async () => {
        const query = createQuerySelection(params);
        await expect(query(9, 9, 0.5)).resolves.toEqual({
            x: 10,
            y: 10,
            category: INCLUDED_BY_FILTERS_CATEGORY,
            identifier: 'sample-b'
        });
    });

    test('returns null beyond the hover radius, for hidden points, and without data', async () => {
        const query = createQuerySelection(params);
        // Nearest point is ~7 units away; radius is 10px * 0.1 units/px = 1 unit.
        await expect(query(5, 5, 0.1)).resolves.toBeNull();

        // Point at (0, 0) is hidden, so hovering right on it yields nothing.
        const hiddenQuery = createQuerySelection({
            ...params,
            category: new Uint8Array([HIDDEN_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY])
        });
        await expect(hiddenQuery(0, 0, 0.5)).resolves.toBeNull();

        const emptyQuery = createQuerySelection({ ...params, sampleIds: undefined });
        await expect(emptyQuery(0, 0, 0.5)).resolves.toBeNull();
    });
});

describe('createThumbnailUrlResolver', () => {
    test('builds image thumbnail URLs directly from the sample ID', async () => {
        const resolve = createThumbnailUrlResolver({ route: 'images', collectionId: 'col-1' });
        await expect(resolve('sample-a')).resolves.toBe(
            'https://example.com/images/sample/sample-a?quality=high&max_width=256&max_height=256'
        );
    });

    test('resolves videos via their poster frame and caches the lookup', async () => {
        getVideoById.mockResolvedValue({ data: { frame: { sample_id: 'frame-1' } } });
        const resolve = createThumbnailUrlResolver({ route: 'videos', collectionId: 'col-1' });

        await expect(resolve('video-1')).resolves.toBe(
            'https://example.com/frames/frame-1?quality=high&max_width=256&max_height=256'
        );
        await resolve('video-1');
        expect(getVideoById).toHaveBeenCalledTimes(1);
        expect(getVideoById).toHaveBeenCalledWith({ path: { sample_id: 'video-1' } });
    });

    test("resolves annotations via the parent sample's image", async () => {
        getAnnotation.mockResolvedValue({ data: { parent_sample_id: 'parent-1' } });
        const resolve = createThumbnailUrlResolver({ route: 'annotations', collectionId: 'col-1' });

        await expect(resolve('annotation-1')).resolves.toBe(
            'https://example.com/images/sample/parent-1?quality=high&max_width=256&max_height=256'
        );
        expect(getAnnotation).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', annotation_id: 'annotation-1' }
        });
    });

    test('resolves to null when the API lookup fails', async () => {
        getVideoById.mockRejectedValue(new Error('network'));
        const resolve = createThumbnailUrlResolver({ route: 'videos', collectionId: 'col-1' });
        await expect(resolve('video-1')).resolves.toBeNull();
    });
});
