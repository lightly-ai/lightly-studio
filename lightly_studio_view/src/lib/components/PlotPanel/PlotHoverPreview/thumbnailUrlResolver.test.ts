import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createThumbnailResolver } from './thumbnailUrlResolver';

vi.mock('$env/static/public', () => ({
    PUBLIC_SAMPLES_URL: 'https://example.com/images',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: 'https://example.com/frames'
}));

const getVideoById = vi.hoisted(() => vi.fn());
const getAnnotation = vi.hoisted(() => vi.fn());
vi.mock('$lib/api/lightly_studio_local', () => ({ getVideoById, getAnnotation }));

describe('createThumbnailResolver', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('builds image thumbnail URLs directly from the sample ID', async () => {
        const resolve = createThumbnailResolver({ route: 'images', collectionId: 'col-1' });
        await expect(resolve('sample-a')).resolves.toEqual({
            url: 'https://example.com/images/sample/sample-a?quality=high&max_width=256&max_height=256'
        });
    });

    it('resolves videos via their poster frame and caches the lookup', async () => {
        getVideoById.mockResolvedValue({ data: { frame: { sample_id: 'frame-1' } } });
        const resolve = createThumbnailResolver({ route: 'videos', collectionId: 'col-1' });

        await expect(resolve('video-1')).resolves.toEqual({
            url: 'https://example.com/frames/frame-1?quality=high&max_width=256&max_height=256'
        });
        await resolve('video-1');
        expect(getVideoById).toHaveBeenCalledTimes(1);
        expect(getVideoById).toHaveBeenCalledWith({ path: { sample_id: 'video-1' } });
    });

    it("resolves annotations via the parent sample's image", async () => {
        const annotation = {
            parent_sample_id: 'parent-1',
            annotation_type: 'object_detection',
            annotation_label: { annotation_label_name: 'traffic light' },
            object_detection_details: { x: 10, y: 20, width: 30, height: 40 }
        };
        getAnnotation.mockResolvedValue({ data: annotation });
        const resolve = createThumbnailResolver({ route: 'annotations', collectionId: 'col-1' });

        await expect(resolve('annotation-1')).resolves.toEqual({
            url: 'https://example.com/images/sample/parent-1',
            annotation
        });
        expect(getAnnotation).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', annotation_id: 'annotation-1' }
        });
    });

    it('retries a failed API lookup for the same sample', async () => {
        getVideoById
            .mockRejectedValueOnce(new Error('network'))
            .mockResolvedValueOnce({ data: { frame: { sample_id: 'frame-1' } } });
        const resolve = createThumbnailResolver({ route: 'videos', collectionId: 'col-1' });

        await expect(resolve('video-1')).resolves.toBeNull();
        await expect(resolve('video-1')).resolves.toEqual({
            url: 'https://example.com/frames/frame-1?quality=high&max_width=256&max_height=256'
        });
        expect(getVideoById).toHaveBeenCalledTimes(2);
    });
});
