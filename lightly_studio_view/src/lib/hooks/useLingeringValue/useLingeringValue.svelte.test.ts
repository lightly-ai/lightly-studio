import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLingeringValue } from './useLingeringValue.svelte';

describe('useLingeringValue', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('shows a value at once and keeps it for the hide delay after it clears', () => {
        let value = $state<string | null>(null);
        let lingering: { readonly current: string | null } | undefined;
        const destroy = $effect.root(() => {
            lingering = useLingeringValue(() => value, 400);
        });

        value = 'pick';
        flushSync();
        expect(lingering?.current).toBe('pick');

        value = null;
        flushSync();
        vi.advanceTimersByTime(399);
        expect(lingering?.current).toBe('pick');

        vi.advanceTimersByTime(1);
        expect(lingering?.current).toBeNull();
        destroy();
    });

    it('keeps showing a value that comes back before the hide delay ends', () => {
        let value = $state<string | null>('pick');
        let lingering: { readonly current: string | null } | undefined;
        const destroy = $effect.root(() => {
            lingering = useLingeringValue(() => value, 400);
        });
        flushSync();

        value = null;
        flushSync();
        vi.advanceTimersByTime(300);
        value = 'add';
        flushSync();
        vi.advanceTimersByTime(400);
        expect(lingering?.current).toBe('add');
        destroy();
    });
});
