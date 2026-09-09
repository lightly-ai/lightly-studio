import type { PointCloudFrame } from '../domain';

/** LRU cache bounded by packed point-buffer bytes and entry count. */
export class FrameCache {
    readonly #frames = new Map<string, PointCloudFrame>();
    #bytes = 0;

    constructor(
        private readonly maxBytes: number,
        private readonly maxEntries = 16
    ) {
        if (
            !Number.isSafeInteger(maxBytes) ||
            maxBytes < 0 ||
            !Number.isSafeInteger(maxEntries) ||
            maxEntries < 0
        ) {
            throw new Error('Frame cache limits must be non-negative integers.');
        }
    }

    get bytes(): number {
        return this.#bytes;
    }

    get(key: string): PointCloudFrame | undefined {
        const frame = this.#frames.get(key);
        if (frame) {
            this.#frames.delete(key);
            this.#frames.set(key, frame);
        }
        return frame;
    }

    set(key: string, frame: PointCloudFrame): void {
        this.delete(key);
        const bytes = this.size(frame);
        if (bytes > this.maxBytes || this.maxEntries === 0) return;
        this.#frames.set(key, frame);
        this.#bytes += bytes;
        while (this.#bytes > this.maxBytes || this.#frames.size > this.maxEntries) {
            this.delete(this.#frames.keys().next().value!);
        }
    }

    clear(): void {
        this.#frames.clear();
        this.#bytes = 0;
    }

    private delete(key: string): void {
        const frame = this.#frames.get(key);
        if (frame) this.#bytes -= this.size(frame);
        this.#frames.delete(key);
    }

    private size(frame: PointCloudFrame): number {
        return (
            4 *
            (frame.positions.length + (frame.intensity?.length ?? 0) + (frame.color?.length ?? 0))
        );
    }
}
