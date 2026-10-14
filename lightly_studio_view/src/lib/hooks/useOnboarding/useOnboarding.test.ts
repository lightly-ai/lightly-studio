import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('image tour invitation', () => {
    beforeEach(() => {
        const values = new Map<string, string>();
        vi.stubGlobal('localStorage', {
            getItem: (key: string) => values.get(key) ?? null,
            setItem: (key: string, value: string) => values.set(key, value)
        });
        vi.resetModules();
    });

    afterEach(() => vi.unstubAllGlobals());

    it('appears once per browser and supports replay', async () => {
        const { useOnboarding, ONBOARDING_STORAGE_KEY } = await import('./useOnboarding');
        const first = useOnboarding();

        expect(first.invite()).toBe(true);
        expect(localStorage.getItem(ONBOARDING_STORAGE_KEY)).toBe('shown');
        first.dismiss();
        expect(useOnboarding().invite()).toBe(false);

        first.replay();
        expect(get(first.state)).toBe('running');
    });

    it('still offers one invitation when storage fails', async () => {
        const { useOnboarding } = await import('./useOnboarding');
        vi.spyOn(localStorage, 'getItem').mockImplementation(() => {
            throw new Error('storage unavailable');
        });
        const first = useOnboarding();

        expect(first.invite()).toBe(true);
        expect(useOnboarding().invite()).toBe(false);
        expect(get(first.state)).toBe('invited');
        vi.restoreAllMocks();
    });
});
