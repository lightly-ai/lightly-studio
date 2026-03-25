import { describe, it, expect } from 'vitest';
import { getURL } from '$lib/utils';

describe('getURL', () => {
    it('should return base path when no params provided', () => {
        const result = getURL('/api/data');
        expect(result).toBe('/api/data');
    });

    it('should append query parameters', () => {
        const result = getURL('/api/data', { id: '123', page: 1 });
        expect(result).toBe('/api/data?id=123&page=1');
    });

    it('should filter out undefined values', () => {
        const result = getURL('/api/data', { id: '123', optional: undefined });
        expect(result).toBe('/api/data?id=123');
    });

    it('should encode special characters in URL params', () => {
        const result = getURL('/api/data', { query: 'hello world', special: 'a&b=c' });
        expect(result).toBe('/api/data?query=hello+world&special=a%26b%3Dc');
    });

    it('should filter out empty string values', () => {
        const result = getURL('/api/data', { id: '', page: 1 });
        expect(result).toBe('/api/data?page=1');
    });

    it('should pass zero values', () => {
        const result = getURL('/api/data', { count: 0, offset: 0 });
        expect(result).toBe('/api/data?count=0&offset=0');
    });
});
