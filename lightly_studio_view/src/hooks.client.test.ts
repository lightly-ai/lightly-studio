import { describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/registerApiErrorInterceptor', () => ({
    registerApiErrorInterceptor: vi.fn()
}));

const { registerApiErrorInterceptor } = await import('$lib/api/registerApiErrorInterceptor');

describe('hooks.client', () => {
    it('registers the API error interceptor', async () => {
        await import('./hooks.client');

        expect(registerApiErrorInterceptor).toHaveBeenCalledOnce();
    });
});
