import { readable, type Readable } from 'svelte/store';

const TICK_MS = 1000;

/** Counts the milliseconds since `startedAt`. The timer runs only while a subscriber exists. */
export function useElapsedTime(startedAt: number): Readable<number> {
    return readable(Date.now() - startedAt, (set) => {
        const timer = setInterval(() => set(Date.now() - startedAt), TICK_MS);
        return () => clearInterval(timer);
    });
}
