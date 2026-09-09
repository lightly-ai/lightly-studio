import { vi } from 'vitest';
import { getMcapRecordingURLById } from './getMcapRecordingURLById';

vi.mock('$env/static/public', () => ({
    PUBLIC_MCAP_MEDIA_URL: 'https://example.com/mcap/media'
}));

describe('getMcapRecordingURLById', () => {
    test('returns the recording URL for a sample ID', () => {
        expect(getMcapRecordingURLById('sample123')).toBe(
            'https://example.com/mcap/media/sample123'
        );
    });

    test('handles empty string', () => {
        expect(getMcapRecordingURLById('')).toBe('https://example.com/mcap/media/');
    });
});
