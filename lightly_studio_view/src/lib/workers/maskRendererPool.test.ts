import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const createMockWorkerClass = () => {
    class MockWorker {
        static instances: MockWorker[] = [];

        terminate = vi.fn();
        addEventListener = vi.fn();
        removeEventListener = vi.fn();
        postMessage = vi.fn();

        constructor() {
            MockWorker.instances.push(this);
        }
    }

    return MockWorker;
};

describe('maskRendererPool', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('creates a capped pool from hardware concurrency and reuses workers', async () => {
        const MockWorker = createMockWorkerClass();
        vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
        vi.stubGlobal('navigator', { hardwareConcurrency: 8 } as Navigator);

        const { acquireMaskRendererWorker, releaseMaskRendererWorker } = await import(
            './maskRendererPool'
        );

        const acquiredWorkers = Array.from({ length: 5 }, () => acquireMaskRendererWorker());

        expect(MockWorker.instances).toHaveLength(4);
        expect(new Set(acquiredWorkers.slice(0, 4)).size).toBe(4);
        expect(acquiredWorkers[4]).toBe(acquiredWorkers[0]);

        for (const worker of acquiredWorkers) {
            releaseMaskRendererWorker(worker);
        }

        for (const instance of MockWorker.instances) {
            expect(instance.terminate).toHaveBeenCalledTimes(1);
        }
    });

    it('falls back to a single worker when hardware concurrency is unavailable', async () => {
        const MockWorker = createMockWorkerClass();
        vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
        vi.stubGlobal('navigator', {} as Navigator);

        const { acquireMaskRendererWorker, releaseMaskRendererWorker } = await import(
            './maskRendererPool'
        );

        const first = acquireMaskRendererWorker();
        const second = acquireMaskRendererWorker();

        expect(MockWorker.instances).toHaveLength(1);
        expect(first).toBe(second);

        releaseMaskRendererWorker(first);
        expect(MockWorker.instances[0].terminate).not.toHaveBeenCalled();

        releaseMaskRendererWorker(second);
        expect(MockWorker.instances[0].terminate).toHaveBeenCalledTimes(1);
    });

    it('ignores releases for workers outside the pool', async () => {
        const MockWorker = createMockWorkerClass();
        vi.stubGlobal('Worker', MockWorker as unknown as typeof Worker);
        vi.stubGlobal('navigator', { hardwareConcurrency: 2 } as Navigator);

        const { acquireMaskRendererWorker, releaseMaskRendererWorker } = await import(
            './maskRendererPool'
        );

        const worker = acquireMaskRendererWorker();
        const unknownWorker = { terminate: vi.fn() } as unknown as Worker;

        releaseMaskRendererWorker(unknownWorker);
        expect(MockWorker.instances[0].terminate).not.toHaveBeenCalled();

        releaseMaskRendererWorker(worker);
        expect(MockWorker.instances[0].terminate).toHaveBeenCalledTimes(1);
    });
});
