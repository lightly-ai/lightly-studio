type WorkerEntry = {
    worker: Worker;
    refCount: number;
};

const createMaskRendererWorker = (): Worker =>
    new Worker(new URL('./maskRenderer.worker.ts', import.meta.url), {
        type: 'module'
    });

const DEFAULT_POOL_SIZE = 1;
const MAX_POOL_SIZE = 4;

const getHardwareConcurrency = (): number | null => {
    if (typeof navigator === 'undefined') {
        return null;
    }

    const value = Math.floor(Number(navigator.hardwareConcurrency));

    if (!Number.isFinite(value) || value < 1) {
        return null;
    }

    return value;
};

const getWorkerPoolSize = (): number => {
    const hardwareConcurrency = getHardwareConcurrency();

    if (!hardwareConcurrency) {
        return DEFAULT_POOL_SIZE;
    }

    // Use a subset of logical cores to keep room for the UI/main thread.
    return Math.max(
        DEFAULT_POOL_SIZE,
        Math.min(MAX_POOL_SIZE, Math.floor(hardwareConcurrency / 2))
    );
};

let workerPool: WorkerEntry[] = [];

const initializeWorkerPool = (): void => {
    if (workerPool.length > 0) {
        return;
    }

    // Lazy creation keeps startup cost low when no mask rendering is needed.
    const poolSize = getWorkerPoolSize();
    workerPool = Array.from({ length: poolSize }, () => ({
        worker: createMaskRendererWorker(),
        refCount: 0
    }));
};

const getLeastLoadedWorker = (): WorkerEntry => {
    let selected = workerPool[0];

    for (const entry of workerPool) {
        if (entry.refCount < selected.refCount) {
            selected = entry;
        }
    }

    return selected;
};

export const acquireMaskRendererWorker = (): Worker => {
    initializeWorkerPool();

    // Assign next canvas to the least-loaded worker to spread rendering work.
    const entry = getLeastLoadedWorker();
    entry.refCount += 1;
    return entry.worker;
};

export const releaseMaskRendererWorker = (worker: Worker): void => {
    if (workerPool.length === 0) {
        return;
    }

    const entry = workerPool.find((poolEntry) => poolEntry.worker === worker);

    if (!entry) {
        return;
    }

    entry.refCount = Math.max(0, entry.refCount - 1);
};

export const shutdownMaskRendererPool = (): void => {
    if (workerPool.length === 0) {
        return;
    }

    for (const poolEntry of workerPool) {
        poolEntry.worker.terminate();
    }

    workerPool = [];
};
