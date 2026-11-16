import { describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/registerApiErrorInterceptor', () => ({
    registerApiErrorInterceptor: vi.fn()
}));

const { registerApiErrorInterceptor } = await import('$lib/api/registerApiErrorInterceptor');
await import('./hooks.client');

describe('hooks.client', () => {
    it('registers the API error interceptor', () => {
        expect(registerApiErrorInterceptor).toHaveBeenCalledOnce();
    });
});
