import { describe, expect, it } from 'vitest';
import { getImageURL } from './getImageURL';

describe('getImageURL', () => {
    it('builds the direct sample image URL', () => {
        expect(getImageURL('sample-1')).toBe('http://mock-url.com/sample/sample-1');
    });

    it('preserves the cache-busting version in the direct image URL', () => {
        expect(getImageURL('sample-1', 'abc 123')).toBe(
            'http://mock-url.com/sample/sample-1?v=abc%20123'
        );
    });
});
