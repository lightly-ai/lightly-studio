interface CaptureVideoFramesParams {
    videoUrl: string;
    timestampsS: number[];
    thumbnailWidth: number;
    signal: AbortSignal;
    onFrame: (index: number, objectUrl: string) => void;
}

/**
 * Decode `timestampsS` from `videoUrl` into JPEG thumbnails, reporting each one
 * through `onFrame` as soon as it is available. Object URLs are owned by the
 * caller and must be revoked by it.
 */
export async function captureVideoFrames({
    videoUrl,
    timestampsS,
    thumbnailWidth,
    signal,
    onFrame
}: CaptureVideoFramesParams): Promise<void> {
    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.preload = 'auto';
    video.muted = true;
    video.src = videoUrl;

    try {
        await waitForMediaEvent(video, 'loadeddata', signal);

        const canvas = document.createElement('canvas');
        canvas.width = thumbnailWidth;
        canvas.height = Math.max(
            1,
            Math.round((thumbnailWidth * video.videoHeight) / (video.videoWidth || thumbnailWidth))
        );
        const context = canvas.getContext('2d');
        if (!context) return;

        for (const [index, timestampS] of timestampsS.entries()) {
            if (signal.aborted) return;
            video.currentTime = clampToDuration(timestampS, video.duration);
            await waitForMediaEvent(video, 'seeked', signal);

            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const blob = await toJpegBlob(canvas);
            if (!blob || signal.aborted) return;
            onFrame(index, URL.createObjectURL(blob));
        }
    } finally {
        video.removeAttribute('src');
        video.load();
    }
}

const EPSILON_S = 0.05;
const JPEG_QUALITY = 0.7;

/** Keep the seek target inside the decodable range; unknown durations pass through. */
function clampToDuration(timestampS: number, durationS: number): number {
    const target = Math.max(0, timestampS);
    if (!Number.isFinite(durationS)) return target;
    return Math.min(target, Math.max(0, durationS - EPSILON_S));
}

function toJpegBlob(canvas: HTMLCanvasElement): Promise<Blob | null> {
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
}

function waitForMediaEvent(
    video: HTMLVideoElement,
    eventName: 'loadeddata' | 'seeked',
    signal: AbortSignal
): Promise<void> {
    return new Promise((resolve, reject) => {
        const abort = () => reject(new DOMException('Aborted', 'AbortError'));
        if (signal.aborted) {
            abort();
            return;
        }

        const cleanup = () => {
            video.removeEventListener(eventName, onDone);
            video.removeEventListener('error', onError);
            signal.removeEventListener('abort', onAbort);
        };
        const onDone = () => {
            cleanup();
            resolve();
        };
        const onError = () => {
            cleanup();
            reject(new Error(`Failed to decode video while waiting for "${eventName}"`));
        };
        const onAbort = () => {
            cleanup();
            abort();
        };

        video.addEventListener(eventName, onDone, { once: true });
        video.addEventListener('error', onError, { once: true });
        signal.addEventListener('abort', onAbort, { once: true });
    });
}
