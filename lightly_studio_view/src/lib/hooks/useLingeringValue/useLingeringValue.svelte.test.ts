import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLingeringValue, type UseLingeringValueReturn } from './useLingeringValue.svelte';

const setup = (hideAtOnce = false) => {
    const source = $state<{ value: string | null }>({ value: 'pick' });
    let lingering: UseLingeringValueReturn<string> | undefined;
    const getHideAtOnce = () => hideAtOnce;
    const destroy = $effect.root(() => {
        lingering = useLingeringValue(() => source.value, 400, getHideAtOnce);
    });
    const set = (value: string | null) => {
        source.value = value;
        flushSync();
    };
    flushSync();
    return { set, current: () => lingering?.current, destroy };
};

describe('useLingeringValue', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('keeps a cleared value for the hide delay', () => {
        const { set, current, destroy } = setup();
        expect(current()).toBe('pick');

        set(null);
        vi.advanceTimersByTime(399);
        expect(current()).toBe('pick');
        vi.advanceTimersByTime(1);
        expect(current()).toBeNull();
        destroy();
    });

    it('keeps showing a value that comes back before the hide delay ends', () => {
        const { set, current, destroy } = setup();
        set(null);
        vi.advanceTimersByTime(300);
        set('add');
        vi.advanceTimersByTime(400);
        expect(current()).toBe('add');
        destroy();
    });

    it('drops a cleared value at once while hideAtOnce is true', () => {
        const { set, current, destroy } = setup(true);
        set(null);
        expect(current()).toBeNull();
        destroy();
    });
});
