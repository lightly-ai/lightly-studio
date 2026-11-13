import { describe, expect, it } from 'vitest';
import { ApiError, getErrorMessage } from './ApiError';

describe('ApiError.fromResponseBody', () => {
    it('reads the message from an error body', () => {
        expect(ApiError.fromResponseBody({ error: 'Provider unavailable' }, 503).message).toBe(
            'Provider unavailable'
        );
        expect(ApiError.fromResponseBody({ detail: 'Not found' }, 404).message).toBe('Not found');
        expect(
            ApiError.fromResponseBody(
                { detail: [{ loc: ['body'], msg: 'Field required', type: 'missing' }] },
                422
            ).message
        ).toBe('Field required');
        expect(ApiError.fromResponseBody('Internal Server Error', 500).message).toBe(
            'Internal Server Error'
        );
    });

    it('reads the message and type of a structured detail', () => {
        const error = ApiError.fromResponseBody(
            { detail: { type: 'transform_unavailable', message: 'No transform' } },
            400
        );

        expect(error).toMatchObject({ message: 'No transform', type: 'transform_unavailable' });
    });

    it('falls back to the status if the body has no message', () => {
        const error = ApiError.fromResponseBody({ detail: [] }, 422);

        expect(error.message).toBe('Request failed with status 422.');
        expect(error.status).toBe(422);
        expect(ApiError.fromResponseBody('', 502).message).toBe('Request failed with status 502.');
        expect(ApiError.fromResponseBody({ error: '', detail: 'Gone' }, 410).message).toBe('Gone');
    });
});

describe('getErrorMessage', () => {
    it('falls back if the error has no message', () => {
        expect(getErrorMessage(new Error('Failed'), 'Unknown error')).toBe('Failed');
        expect(getErrorMessage(new Error(''), 'Unknown error')).toBe('Unknown error');
        expect(getErrorMessage('Failed', 'Unknown error')).toBe('Unknown error');
    });
});
