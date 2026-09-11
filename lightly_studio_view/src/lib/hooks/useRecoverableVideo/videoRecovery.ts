interface VideoPlaybackSnapshot {
    currentTime: number;
    muted: boolean;
    playbackRate: number;
    shouldPlay: boolean;
    volume: number;
}

export function captureVideoPlayback(
    video: HTMLVideoElement,
    shouldPlay: boolean
): VideoPlaybackSnapshot {
    return {
        currentTime: Number.isFinite(video.currentTime) ? video.currentTime : 0,
        muted: video.muted,
        playbackRate: video.playbackRate,
        shouldPlay,
        volume: video.volume
    };
}

export async function restoreVideoPlayback(
    video: HTMLVideoElement,
    snapshot: VideoPlaybackSnapshot,
    signal: AbortSignal
): Promise<boolean> {
    await waitForMetadata(video, signal);
    if (signal.aborted) return false;

    video.muted = snapshot.muted;
    video.playbackRate = snapshot.playbackRate;
    video.volume = snapshot.volume;
    video.currentTime = snapshot.currentTime;
    if (!snapshot.shouldPlay) return true;

    try {
        await video.play();
        return true;
    } catch {
        return false;
    }
}

function waitForMetadata(video: HTMLVideoElement, signal: AbortSignal): Promise<void> {
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
        return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        const cleanup = () => {
            video.removeEventListener('loadedmetadata', handleLoadedMetadata);
            video.removeEventListener('error', handleError);
            signal.removeEventListener('abort', handleAbort);
        };
        const handleLoadedMetadata = () => {
            cleanup();
            resolve();
        };
        const handleError = () => {
            cleanup();
            reject(new Error('The proxy video source failed to load.'));
        };
        const handleAbort = () => {
            cleanup();
            reject(new DOMException('Video recovery was cancelled.', 'AbortError'));
        };
        video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
        video.addEventListener('error', handleError, { once: true });
        signal.addEventListener('abort', handleAbort, { once: true });
    });
}
