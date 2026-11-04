import { getErrorMessage } from './getErrorMessage';

describe('getErrorMessage', () => {
    test('returns the message of an Error', () => {
        expect(getErrorMessage(new Error('Network failure'))).toBe('Network failure');
    });

    test('returns the message of an error object', () => {
        expect(getErrorMessage({ name: 'TestError', message: 'Failed' })).toBe('Failed');
    });

    test('returns undefined for an API error body without a message', () => {
        expect(getErrorMessage({ detail: [] })).toBeUndefined();
    });

    test('returns undefined for null', () => {
        expect(getErrorMessage(null)).toBeUndefined();
    });
});
