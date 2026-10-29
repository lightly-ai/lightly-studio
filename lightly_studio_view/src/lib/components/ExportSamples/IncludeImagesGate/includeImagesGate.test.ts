import { describe, expect, it } from 'vitest';
import {
    formatBytes,
    getIncludeImagesState,
    MAX_BROWSER_DOWNLOAD_BYTES
} from './includeImagesGate';

describe('formatBytes', () => {
    it('picks a readable unit', () => {
        expect(formatBytes(380 * 1024 ** 2)).toBe('380 MB');
        expect(formatBytes(1.9 * 1024 ** 3)).toBe('1.9 GB');
        expect(formatBytes(512)).toBe('1 KB');
    });
});

describe('getIncludeImagesState', () => {
    it('allows images while the estimate loads', () => {
        expect(getIncludeImagesState(undefined)).toEqual({ allowed: true, sizeText: undefined });
    });

    it('shows the count and size below the limit', () => {
        expect(
            getIncludeImagesState({ image_count: 5000, estimated_bytes: 1.9 * 1024 ** 3 })
        ).toEqual({ allowed: true, sizeText: '5,000 images, about 1.9 GB' });
    });

    it('shows only the count when no file size could be read', () => {
        expect(getIncludeImagesState({ image_count: 12, estimated_bytes: null })).toEqual({
            allowed: true,
            sizeText: '12 images'
        });
    });

    it('blocks the browser download above the limit and points to the code export', () => {
        const state = getIncludeImagesState({
            image_count: 40000,
            estimated_bytes: MAX_BROWSER_DOWNLOAD_BYTES + 1
        });

        expect(state.allowed).toBe(false);
        expect(state.sizeText).toBe('40,000 images, about 2 GB');
        expect(state.reason).toContain('Copy as code');
    });
});
