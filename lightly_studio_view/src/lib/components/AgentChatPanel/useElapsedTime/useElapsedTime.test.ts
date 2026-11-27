import { afterEach, describe, expect, it, vi } from 'vitest';
import { useElapsedTime } from './useElapsedTime';

describe('useElapsedTime', () => {
    afterEach(() => vi.useRealTimers());

    it('counts up once per second while subscribed', () => {
        vi.useFakeTimers({ now: 10_000 });
        const values: number[] = [];
        const unsubscribe = useElapsedTime(8_000).subscribe((value) => values.push(value));

        vi.advanceTimersByTime(2_000);
        unsubscribe();
        vi.advanceTimersByTime(5_000);

        expect(values).toEqual([2_000, 3_000, 4_000]);
    });
});
