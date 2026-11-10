import { describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/lightly_studio_local/client.gen', () => ({
    client: { interceptors: { error: { use: vi.fn() } } }
}));

const { client } = await import('$lib/api/lightly_studio_local/client.gen');
await import('./hooks.client');

const [interceptor] = vi.mocked(client.interceptors.error.use).mock.calls[0];
const request = new Request('http://localhost');
const options = {} as Parameters<typeof interceptor>[3];

describe('hooks.client error interceptor', () => {
    it('rethrows a failure without a response', () => {
        const error = new TypeError('Failed to fetch');
        expect(() => interceptor(error, undefined, request, options)).toThrow(error);
    });

    it('adds the HTTP status to the error body', () => {
        const result = interceptor(
            { detail: 'Not found' },
            new Response(null, { status: 404 }),
            request,
            options
        );
        expect(result).toEqual({ detail: 'Not found', status: 404 });
    });

    it('returns a text body unchanged', () => {
        const result = interceptor(
            'Bad Gateway',
            new Response(null, { status: 502 }),
            request,
            options
        );
        expect(result).toBe('Bad Gateway');
    });
});
