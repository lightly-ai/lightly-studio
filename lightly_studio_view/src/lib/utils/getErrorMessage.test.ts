import { describe, expect, it } from 'vitest';
import { getErrorMessage } from './getErrorMessage';

describe('getErrorMessage', () => {
    it('returns the message of an Error', () => {
        expect(getErrorMessage(new Error('Network down'))).toBe('Network down');
    });

    it('returns the message of an object with a message', () => {
        expect(getErrorMessage({ message: 'Bad request' })).toBe('Bad request');
    });

    it('returns undefined for an API error body without a message', () => {
        expect(getErrorMessage({ detail: [] })).toBeUndefined();
    });

    it('returns undefined for a non-string message', () => {
        expect(getErrorMessage({ message: 42 })).toBeUndefined();
    });

    it('returns undefined for null', () => {
        expect(getErrorMessage(null)).toBeUndefined();
    });
});
