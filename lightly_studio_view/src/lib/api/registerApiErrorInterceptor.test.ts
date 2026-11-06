import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './ApiError';
import { client } from './lightly_studio_local/client.gen';

// setupTests.ts registers the interceptor, as hooks.client.ts does in the app.
const get = (fetch: typeof globalThis.fetch) => client.get({ url: '/items', fetch });

describe('registerApiErrorInterceptor', () => {
    it('returns an HTTP error as an ApiError', async () => {
        const fetch = vi
            .fn()
            .mockResolvedValue(Response.json({ detail: 'Not found' }, { status: 404 }));

        const { error } = await get(fetch);

        expect(error).toBeInstanceOf(ApiError);
        expect(error).toMatchObject({ message: 'Not found', status: 404 });
    });

    it('rejects on a network failure', async () => {
        const fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

        await expect(get(fetch)).rejects.toThrow('Failed to fetch');
    });

    it('rejects if a successful response cannot be parsed', async () => {
        const fetch = vi
            .fn()
            .mockResolvedValue(
                new Response('{', { headers: { 'Content-Type': 'application/json' } })
            );

        await expect(get(fetch)).rejects.toBeInstanceOf(SyntaxError);
    });
});
