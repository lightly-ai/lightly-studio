import type { FrameView, VideoFrameView } from '$lib/api/lightly_studio_local';

export type PlaybackSelectionStrategy = 'frame_start' | 'midpoint';

export interface FrameWindowTarget<TFrame extends FrameView | VideoFrameView> {
    frame: TFrame;
    index: number;
    selectedTimestamp: number;
    windowStartTimestamp: number;
    windowEndTimestamp: number;
    seekTargetTime: number;
}

export interface PlaybackFrameSelection<TFrame extends FrameView | VideoFrameView> {
    frame: TFrame | null;
    index: number | null;
    selectedTimestamp: number | null;
    windowStartTimestamp: number | null;
    windowEndTimestamp: number | null;
    nextTimestamp: number | null;
    selectorInvariantHolds: boolean;
    sourceTime: number;
    strategy: PlaybackSelectionStrategy;
}

export function selectPlaybackFrame<TFrame extends FrameView | VideoFrameView>({
    frames,
    sourceTime,
    strategy = 'frame_start'
}: {
    frames: TFrame[];
    sourceTime: number;
    strategy?: PlaybackSelectionStrategy;
}): PlaybackFrameSelection<TFrame> {
    if (!frames.length) {
        return {
            frame: null,
            index: null,
            selectedTimestamp: null,
            windowStartTimestamp: null,
            windowEndTimestamp: null,
            nextTimestamp: null,
            selectorInvariantHolds: true,
            sourceTime,
            strategy
        };
    }

    let low = 0;
    let high = frames.length - 1;
    let best = 0;

    if (strategy === 'frame_start') {
        while (low <= high) {
            const mid = Math.floor((low + high) / 2);
            const ts = frames[mid].frame_timestamp_s;

            if (ts <= sourceTime) {
                best = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
    } else {
        let firstGreater = frames.length;

        while (low <= high) {
            const mid = Math.floor((low + high) / 2);
            const ts = frames[mid].frame_timestamp_s;

            if (ts > sourceTime) {
                firstGreater = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }

        if (firstGreater === 0) {
            best = 0;
        } else if (firstGreater === frames.length) {
            best = frames.length - 1;
        } else {
            const previousIndex = firstGreater - 1;
            const midpoint =
                (frames[previousIndex].frame_timestamp_s + frames[firstGreater].frame_timestamp_s) /
                2;
            best = sourceTime < midpoint ? previousIndex : firstGreater;
        }
    }

    const frame = frames[best];
    const selectedTimestamp = frame.frame_timestamp_s;
    const previousFrame = frames[best - 1];
    const nextFrame = frames[best + 1];
    const nextTimestamp = nextFrame ? nextFrame.frame_timestamp_s : null;
    const windowStartTimestamp =
        strategy === 'frame_start'
            ? selectedTimestamp
            : previousFrame
              ? (previousFrame.frame_timestamp_s + selectedTimestamp) / 2
              : null;
    const windowEndTimestamp =
        strategy === 'frame_start'
            ? nextTimestamp
            : nextFrame
              ? (selectedTimestamp + nextFrame.frame_timestamp_s) / 2
              : null;

    return {
        frame,
        index: best,
        selectedTimestamp,
        windowStartTimestamp,
        windowEndTimestamp,
        nextTimestamp,
        selectorInvariantHolds:
            (windowStartTimestamp === null || windowStartTimestamp <= sourceTime) &&
            (windowEndTimestamp === null || sourceTime < windowEndTimestamp),
        sourceTime,
        strategy
    };
}

export function findFrame({
    frames,
    currentTime
}: {
    frames: FrameView[] | VideoFrameView[];
    currentTime: number;
}): { frame: FrameView | VideoFrameView | null; index: number | null } {
    const selection = selectPlaybackFrame({ frames, sourceTime: currentTime });
    return { frame: selection.frame, index: selection.index };
}

export function getFrameWindowTarget<TFrame extends FrameView | VideoFrameView>({
    frames,
    frameIndex,
    videoDuration
}: {
    frames: TFrame[];
    frameIndex: number;
    videoDuration?: number | null;
}): FrameWindowTarget<TFrame> | null {
    if (!frames.length) {
        return null;
    }

    const safeIndex = Math.max(0, Math.min(frameIndex, frames.length - 1));
    const frame = frames[safeIndex];
    const selectedTimestamp = frame.frame_timestamp_s;
    const nextFrame = frames[safeIndex + 1];
    const previousFrame = frames[safeIndex - 1];
    const fallbackTail =
        previousFrame != null
            ? Math.max(selectedTimestamp - previousFrame.frame_timestamp_s, 0.001)
            : 0.001;
    const durationBoundary =
        typeof videoDuration === 'number' &&
        Number.isFinite(videoDuration) &&
        videoDuration > selectedTimestamp
            ? videoDuration
            : null;
    const windowStartTimestamp = selectedTimestamp;
    const windowEndTimestamp = nextFrame
        ? nextFrame.frame_timestamp_s
        : (durationBoundary ?? selectedTimestamp + fallbackTail);

    return {
        frame,
        index: safeIndex,
        selectedTimestamp,
        windowStartTimestamp,
        windowEndTimestamp,
        seekTargetTime: (windowStartTimestamp + windowEndTimestamp) / 2
    };
}
