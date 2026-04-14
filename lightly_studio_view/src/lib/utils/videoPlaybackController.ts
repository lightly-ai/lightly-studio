import type { FrameView, VideoFrameView } from '$lib/api/lightly_studio_local';
import {
    selectPlaybackFrame,
    type PlaybackFrameSelection,
    type PlaybackSelectionStrategy
} from '$lib/utils/frame';

export type PlaybackSource = 'rvfc' | 'raf' | 'event';
export type PlaybackClockMode = 'auto' | 'rvfc' | 'raf';

type VideoFrameRequestCallback = (
    now: DOMHighResTimeStamp,
    metadata: VideoFrameCallbackMetadata
) => void;

type VideoElementWithRVFC = HTMLVideoElement & {
    requestVideoFrameCallback?: (callback: VideoFrameRequestCallback) => number;
    cancelVideoFrameCallback?: (handle: number) => void;
};

export interface PlaybackSample<TFrame extends FrameView | VideoFrameView> {
    clockTime: number;
    currentTime: number;
    mediaTime: number | null;
    source: PlaybackSource;
    selection: PlaybackFrameSelection<TFrame>;
}

interface CreateVideoPlaybackControllerOptions<TFrame extends FrameView | VideoFrameView> {
    videoEl: HTMLVideoElement;
    frames: TFrame[];
    emitDuplicateFrames?: boolean;
    clockMode?: PlaybackClockMode;
    selectionStrategy?:
        | PlaybackSelectionStrategy
        | ((params: {
              source: PlaybackSource;
              currentTime: number;
              mediaTime: number | null;
          }) => PlaybackSelectionStrategy);
    onSample: (sample: PlaybackSample<TFrame>) => void;
}

export function createVideoPlaybackController<TFrame extends FrameView | VideoFrameView>({
    videoEl,
    frames,
    emitDuplicateFrames = false,
    clockMode = 'auto',
    selectionStrategy = 'frame_start',
    onSample
}: CreateVideoPlaybackControllerOptions<TFrame>) {
    const video = videoEl as VideoElementWithRVFC;
    let rafId: number | null = null;
    let rvfcId: number | null = null;
    let previousFrameId: string | null = null;
    let lastMediaTime: number | null = null;

    const cancelScheduledCallback = () => {
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }

        if (rvfcId !== null && video.cancelVideoFrameCallback) {
            video.cancelVideoFrameCallback(rvfcId);
            rvfcId = null;
        }
    };

    const emitSample = ({
        source,
        clockTime,
        mediaTime
    }: {
        source: PlaybackSource;
        clockTime: number;
        mediaTime: number | null;
    }) => {
        const sourceTime = mediaTime ?? video.currentTime;
        if (mediaTime != null) {
            lastMediaTime = mediaTime;
        }
        const resolvedSelectionStrategy =
            typeof selectionStrategy === 'function'
                ? selectionStrategy({
                      source,
                      currentTime: video.currentTime,
                      mediaTime
                  })
                : selectionStrategy;
        const selection = selectPlaybackFrame({
            frames,
            sourceTime,
            strategy: resolvedSelectionStrategy
        });

        if (!selection.frame) {
            previousFrameId = null;
            return;
        }

        if (
            !emitDuplicateFrames &&
            selection.frame.sample_id === previousFrameId &&
            selection.selectorInvariantHolds
        ) {
            return;
        }

        previousFrameId = selection.frame.sample_id;
        onSample({
            clockTime,
            currentTime: video.currentTime,
            mediaTime: mediaTime ?? lastMediaTime,
            source,
            selection
        });
    };

    const scheduleNext = () => {
        cancelScheduledCallback();

        if (video.paused || video.ended) {
            return;
        }

        const hasRvfc = typeof video.requestVideoFrameCallback === 'function';
        const shouldUseRvfc =
            clockMode === 'raf' ? false : clockMode === 'rvfc' ? hasRvfc : hasRvfc;

        if (shouldUseRvfc) {
            rvfcId = video.requestVideoFrameCallback((now, metadata) => {
                rvfcId = null;
                emitSample({
                    source: 'rvfc',
                    clockTime: now,
                    mediaTime: metadata.mediaTime
                });
                scheduleNext();
            });
            return;
        }

        rafId = requestAnimationFrame((now) => {
            rafId = null;
            emitSample({
                source: 'raf',
                clockTime: now,
                mediaTime: null
            });
            scheduleNext();
        });
    };

    const syncImmediately = () => {
        emitSample({
            source: 'event',
            clockTime: performance.now(),
            mediaTime: null
        });
    };

    const handlePlay = () => scheduleNext();
    const handleLoadedData = () => syncImmediately();
    const handleSeeked = () => syncImmediately();
    const handlePause = () => {
        cancelScheduledCallback();
        syncImmediately();
    };
    const handleEnded = () => {
        cancelScheduledCallback();
        syncImmediately();
    };
    const handleEmptied = () => {
        cancelScheduledCallback();
        previousFrameId = null;
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('emptied', handleEmptied);

    if (!video.paused && !video.ended) {
        scheduleNext();
    }

    return {
        syncImmediately,
        destroy() {
            cancelScheduledCallback();
            video.removeEventListener('play', handlePlay);
            video.removeEventListener('loadeddata', handleLoadedData);
            video.removeEventListener('seeked', handleSeeked);
            video.removeEventListener('pause', handlePause);
            video.removeEventListener('ended', handleEnded);
            video.removeEventListener('emptied', handleEmptied);
        }
    };
}
