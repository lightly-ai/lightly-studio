import { vi } from 'vitest';
import { getVideoURLById } from './getVideoURLById';

// Mock the environment variable
vi.mock('$env/static/public', () => ({
    PUBLIC_VIDEOS_MEDIA_URL: 'https://example.com'
}));

describe('getVideoURLById', () => {
    test('returns correct URL with video ID', () => {
        expect(getVideoURLById('video123')).toBe('https://example.com/video123');
    });

    test('handles empty string', () => {
        expect(getVideoURLById('')).toBe('https://example.com/');
    });
});
