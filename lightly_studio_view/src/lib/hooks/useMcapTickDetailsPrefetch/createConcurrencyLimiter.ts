interface WaitingTask {
    /** Starts the task in a free slot. */
    start: () => void;
    /** Rejects the task without starting it. */
    cancel: (error: Error) => void;
}

/** Runs async tasks with a bounded number active at once, in the order they were submitted. */
export function createConcurrencyLimiter(maxConcurrent: number) {
    let active = 0;
    const waiting: WaitingTask[] = [];

    const startWaiting = () => {
        while (active < maxConcurrent && waiting.length > 0) waiting.shift()?.start();
    };

    return {
        /** Runs a task when a slot is free and settles with the task's result. */
        run<T>(task: () => Promise<T>): Promise<T> {
            return new Promise<T>((resolve, reject) => {
                waiting.push({
                    start: () => {
                        active += 1;
                        Promise.resolve()
                            .then(task)
                            .then(resolve, reject)
                            .finally(() => {
                                active -= 1;
                                startWaiting();
                            });
                    },
                    cancel: reject
                });
                startWaiting();
            });
        },
        /** Rejects the tasks that have not started. Running tasks finish. */
        clear(): void {
            for (const task of waiting.splice(0)) {
                task.cancel(new Error('The prefetch session was discarded.'));
            }
        }
    };
}
