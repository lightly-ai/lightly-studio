import { describe, expect, test, vi } from 'vitest';

import {
    getGridFrameURL,
    getGridImageURL,
    getGridThumbnailRequestSize
} from './getGridThumbnailURL';

vi.mock('$env/static/public', () => ({
    PUBLIC_SAMPLES_URL: 'https://example.com/images',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: 'https://example.com/frames'
}));

describe('getGridThumbnailRequestSize', () => {
    test('caps device pixel ratio at 2', () => {
        expect(getGridThumbnailRequestSize(120, 3)).toBe(240);
    });
});

describe('getGridImageURL', () => {
    test('returns raw image URL with cache buster', () => {
        expect(
            getGridImageURL({
                sampleId: 'sample-1',
                quality: 'raw',
                cacheBuster: '123'
            })
        ).toBe('https://example.com/images/sample/sample-1?v=123');
    });

    test('returns transformed image URL for high quality', () => {
        expect(
            getGridImageURL({
                sampleId: 'sample-1',
                quality: 'high',
                renderedWidth: 240,
                renderedHeight: 160,
                cacheBuster: '123'
            })
        ).toBe(
            'https://example.com/images/sample/sample-1?v=123&quality=high&max_width=240&max_height=160'
        );
    });
});

describe('getGridFrameURL', () => {
    test('returns transformed frame URL for high quality', () => {
        expect(
            getGridFrameURL({
                sampleId: 'frame-1',
                quality: 'high',
                renderedWidth: 120,
                renderedHeight: 120
            })
        ).toBe('https://example.com/frames/frame-1?quality=high&max_width=120&max_height=120');
    });
});
