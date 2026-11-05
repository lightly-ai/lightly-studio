import { getErrorMessage } from './getErrorMessage';

describe('getErrorMessage', () => {
    test('reads the message from the response body', () => {
        expect(getErrorMessage({ error: 'Provider unavailable' })).toBe('Provider unavailable');
        expect(getErrorMessage({ detail: 'Video not found' })).toBe('Video not found');
        expect(
            getErrorMessage({
                detail: [{ loc: ['body', 'prompt'], msg: 'Field required', type: 'missing' }]
            })
        ).toBe('Field required');
    });

    test('reads a plain-text body', () => {
        expect(getErrorMessage('Internal Server Error')).toBe('Internal Server Error');
        expect(getErrorMessage({ error: 'Bad Gateway', status: 502 })).toBe('Bad Gateway');
        expect(getErrorMessage({ error: '', status: 404 })).toBe('Unknown error');
    });

    test('reads the message of an Error', () => {
        expect(getErrorMessage(new Error('Network failure'))).toBe('Network failure');
    });

    test('returns a fallback for an unknown error and undefined for no error', () => {
        expect(getErrorMessage({})).toBe('Unknown error');
        expect(getErrorMessage(null)).toBeUndefined();
        expect(getErrorMessage(undefined)).toBeUndefined();
    });
});
