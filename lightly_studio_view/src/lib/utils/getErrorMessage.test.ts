import { describe, expect, it } from 'vitest';
import { getErrorMessage } from './getErrorMessage';

describe('getErrorMessage', () => {
    it('returns the message of an Error', () => {
        expect(getErrorMessage(new Error('Network down'))).toBe('Network down');
    });

    it('returns the message from an API error body', () => {
        expect(getErrorMessage({ error: 'Provider unavailable' })).toBe('Provider unavailable');
        expect(getErrorMessage({ detail: 'Not found' })).toBe('Not found');
        expect(getErrorMessage({ detail: [{ msg: 'Field required' }] })).toBe('Field required');
    });

    it('returns undefined if there is no message', () => {
        expect(getErrorMessage({ detail: [] })).toBeUndefined();
        expect(getErrorMessage({ message: 42 })).toBeUndefined();
        expect(getErrorMessage(null)).toBeUndefined();
    });
});
