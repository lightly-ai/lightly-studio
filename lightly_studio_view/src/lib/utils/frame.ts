import type { FrameView, VideoFrameView } from '$lib/api/lightly_studio_local';

const EPS = 0.002;

export function getFrameBatchCursor(frameIndex: number, batchSize: number): number {
    if (batchSize <= 0) throw new Error('batchSize must be greater than zero');

    return Math.floor(frameIndex / batchSize) * batchSize;
}

export function findFrame({
    frames,
    currentTime
}: {
    frames: FrameView[] | VideoFrameView[];
    currentTime: number;
}): { frame: FrameView | VideoFrameView | null; index: number | null } {
    if (!frames.length) return { frame: null, index: null };

    let low = 0;
    let high = frames.length - 1;
    let best = 0;

    while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const ts = frames[mid].frame_timestamp_s + EPS;

        if (ts <= currentTime) {
            best = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    return { frame: frames[best], index: best };
}
