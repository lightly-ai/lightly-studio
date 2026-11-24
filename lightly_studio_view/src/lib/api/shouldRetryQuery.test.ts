import { describe, expect, it } from 'vitest';
import { ApiError } from './ApiError';
import { NoRetryError } from './NoRetryError';
import { shouldRetryQuery } from './shouldRetryQuery';

describe('shouldRetryQuery', () => {
    it('retries network and server errors up to 3 times', () => {
        expect(shouldRetryQuery(0, new TypeError('Failed to fetch'))).toBe(true);
        expect(shouldRetryQuery(2, new ApiError('Internal Server Error', 500))).toBe(true);
        expect(shouldRetryQuery(3, new ApiError('Internal Server Error', 500))).toBe(false);
    });

    it('does not retry client errors', () => {
        expect(shouldRetryQuery(0, new ApiError('Not found', 404))).toBe(false);
    });

    it('does not retry a NoRetryError', () => {
        const error = new NoRetryError(new ApiError('Internal Server Error', 500));

        expect(shouldRetryQuery(0, error)).toBe(false);
        expect(error.message).toBe('Internal Server Error');
    });
});
