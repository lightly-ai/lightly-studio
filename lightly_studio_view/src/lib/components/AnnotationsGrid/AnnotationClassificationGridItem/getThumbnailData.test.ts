import { describe, expect, test, vi } from 'vitest';

import {
    SampleType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView
} from '$lib/api/lightly_studio_local';

import { getThumbnailUrl, getSampleDimensions } from './getThumbnailData';

vi.mock('$env/static/public', () => ({
    PUBLIC_SAMPLES_URL: 'https://example.com/images',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: 'https://example.com/frames'
}));

const imageAnnotation: AnnotationWithPayloadView = {
    parent_sample_type: SampleType.IMAGE,
    annotation: {} as AnnotationWithPayloadView['annotation'],
    parent_sample_data: {
        sample_id: 'img-1',
        file_path_abs: '/path/to/img.jpg',
        width: 1920,
        height: 1080,
        sample: {} as ImageAnnotationView['sample']
    } as ImageAnnotationView
};

const videoFrameAnnotation: AnnotationWithPayloadView = {
    parent_sample_type: SampleType.VIDEO_FRAME,
    annotation: {} as AnnotationWithPayloadView['annotation'],
    parent_sample_data: {
        sample_id: 'frame-1',
        video: {
            width: 1280,
            height: 720,
            file_path_abs: '/path/to/video.mp4'
        }
    } as VideoFrameAnnotationView
};

describe('getThumbnailUrl', () => {
    test('returns image URL for image annotation', () => {
        const url = getThumbnailUrl({
            annotation: imageAnnotation,
            quality: 'raw',
            containerWidth: 200,
            containerHeight: 150,
            cachedCollectionVersion: 'v1'
        });
        expect(url).toBe('https://example.com/images/sample/img-1?v=v1');
    });

    test('returns video frame URL for video frame annotation', () => {
        const url = getThumbnailUrl({
            annotation: videoFrameAnnotation,
            quality: 'raw',
            containerWidth: 200,
            containerHeight: 150,
            cachedCollectionVersion: 'v1'
        });
        expect(url).toBe('https://example.com/frames/frame-1');
    });

    test('includes quality params for high quality image', () => {
        vi.stubGlobal('window', { devicePixelRatio: 1 });
        const url = getThumbnailUrl({
            annotation: imageAnnotation,
            quality: 'high',
            containerWidth: 200,
            containerHeight: 150,
            cachedCollectionVersion: 'v2'
        });
        expect(url).toBe(
            'https://example.com/images/sample/img-1?v=v2&quality=high&max_width=200&max_height=150'
        );
        vi.unstubAllGlobals();
    });

    test('includes quality params for high quality video frame', () => {
        vi.stubGlobal('window', { devicePixelRatio: 1 });
        const url = getThumbnailUrl({
            annotation: videoFrameAnnotation,
            quality: 'high',
            containerWidth: 200,
            containerHeight: 150,
            cachedCollectionVersion: 'v2'
        });
        expect(url).toBe(
            'https://example.com/frames/frame-1?quality=high&max_width=200&max_height=150'
        );
        vi.unstubAllGlobals();
    });
});

describe('getSampleDimensions', () => {
    test('returns image dimensions for image annotation', () => {
        expect(getSampleDimensions(imageAnnotation)).toEqual({ width: 1920, height: 1080 });
    });

    test('returns video dimensions for video frame annotation', () => {
        expect(getSampleDimensions(videoFrameAnnotation)).toEqual({ width: 1280, height: 720 });
    });
});
