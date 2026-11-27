import { describe, expect, it } from 'vitest';
import { runOneAtATime } from './runOneAtATime';

describe('runOneAtATime', () => {
    it('starts a call only after the previous one ended', async () => {
        const events: string[] = [];
        const task = runOneAtATime(async (name: string) => {
            events.push(`start ${name}`);
            await new Promise((resolve) => setTimeout(resolve, 5));
            events.push(`end ${name}`);
            return name;
        });

        const results = await Promise.all([task('a'), task('b')]);

        expect(results).toEqual(['a', 'b']);
        expect(events).toEqual(['start a', 'end a', 'start b', 'end b']);
    });

    it('keeps running calls after one fails', async () => {
        const task = runOneAtATime(async (shouldFail: boolean) => {
            if (shouldFail) throw new Error('failed');
            return 'ok';
        });

        const [failed, succeeded] = await Promise.allSettled([task(true), task(false)]);

        expect(failed.status).toBe('rejected');
        expect(succeeded).toEqual({ status: 'fulfilled', value: 'ok' });
    });
});
