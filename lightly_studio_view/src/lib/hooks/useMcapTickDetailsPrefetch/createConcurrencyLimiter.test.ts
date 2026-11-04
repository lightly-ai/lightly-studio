import { describe, expect, it, vi } from 'vitest';
import { createConcurrencyLimiter } from './createConcurrencyLimiter';

function deferred() {
    let resolve!: () => void;
    const promise = new Promise<void>((complete) => (resolve = complete));
    return { promise, resolve };
}

describe('createConcurrencyLimiter', () => {
    it('runs at most the given number of tasks, in submission order', async () => {
        const limiter = createConcurrencyLimiter(2);
        const tasks = [deferred(), deferred(), deferred(), deferred()];
        const started: number[] = [];
        const results = tasks.map((task, index) =>
            limiter.run(() => {
                started.push(index);
                return task.promise.then(() => index);
            })
        );

        await Promise.resolve();
        expect(started).toEqual([0, 1]);

        tasks[1].resolve();
        await vi.waitFor(() => expect(started).toEqual([0, 1, 2]));
        tasks[0].resolve();
        await vi.waitFor(() => expect(started).toEqual([0, 1, 2, 3]));
        tasks[2].resolve();
        tasks[3].resolve();

        expect(await Promise.all(results)).toEqual([0, 1, 2, 3]);
    });

    it('frees a slot when a task rejects', async () => {
        const limiter = createConcurrencyLimiter(1);
        const error = new Error('request failed');

        const failed = limiter.run(() => Promise.reject(error));
        const next = limiter.run(() => Promise.resolve('next'));

        await expect(failed).rejects.toBe(error);
        await expect(next).resolves.toBe('next');
    });

    it('rejects waiting tasks on clear and lets running tasks finish', async () => {
        const limiter = createConcurrencyLimiter(1);
        const running = deferred();
        let waitingStarted = false;
        const first = limiter.run(() => running.promise.then(() => 'first'));
        const waiting = limiter.run(() => {
            waitingStarted = true;
            return Promise.resolve('waiting');
        });

        limiter.clear();
        running.resolve();

        await expect(waiting).rejects.toThrow('discarded');
        await expect(first).resolves.toBe('first');
        expect(waitingStarted).toBe(false);
    });
});
