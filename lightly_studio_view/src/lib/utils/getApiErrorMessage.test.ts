import { describe, expect, it } from 'vitest';
import { getApiErrorMessage } from './getApiErrorMessage';

describe('getApiErrorMessage', () => {
    it('reads the error message from the response body', () => {
        expect(getApiErrorMessage({ error: 'Provider unavailable' })).toBe('Provider unavailable');
        expect(getApiErrorMessage({ detail: 'Bad request' })).toBe('Bad request');
        expect(getApiErrorMessage(new Error('boom'))).toBe('boom');
    });

    it('reads the first message of a validation error', () => {
        expect(
            getApiErrorMessage({
                detail: [{ loc: ['body', 'prompt'], msg: 'Field required', type: 'missing' }]
            })
        ).toBe('Field required');
    });

    it('falls back when the error says nothing usable', () => {
        expect(getApiErrorMessage(undefined)).toBe('Unknown error');
        expect(getApiErrorMessage({}, 'Could not move.')).toBe('Could not move.');
    });

    it('skips empty messages', () => {
        expect(getApiErrorMessage({ error: '', detail: 'Bad request' })).toBe('Bad request');
        expect(getApiErrorMessage({ detail: [{ msg: '' }] })).toBe('Unknown error');
    });
});
