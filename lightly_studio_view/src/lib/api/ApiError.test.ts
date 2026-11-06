import { describe, expect, it } from 'vitest';
import { ApiError } from './ApiError';

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

    it('falls back to the status if the body has no message', () => {
        const error = ApiError.fromResponseBody({ detail: [] }, 422);

        expect(error.message).toBe('Request failed with status 422.');
        expect(error.status).toBe(422);
        expect(ApiError.fromResponseBody('', 502).message).toBe('Request failed with status 502.');
    });
});
