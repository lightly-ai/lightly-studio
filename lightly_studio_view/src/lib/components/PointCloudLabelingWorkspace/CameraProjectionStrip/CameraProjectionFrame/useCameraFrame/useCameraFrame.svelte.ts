import { getCameraFrameUrl } from '../../getCameraFrameUrl/getCameraFrameUrl';
import type { CameraProjectionFrameProps } from '../cameraProjectionFrameProps';
/** Manages image URLs, failure state, and tile sizing for one camera frame. */
export function useCameraFrame(getProps: () => CameraProjectionFrameProps) {
    const datasetId = $derived(getProps().datasetId);
    const recordingId = $derived(getProps().recordingId);
    const channelId = $derived(getProps().channelId);
    const keyframeTimestampNs = $derived(getProps().keyframeTimestampNs);
    const logTimeNs = $derived(getProps().logTimeNs);
    const blob = $derived(getProps().blob);
    const fullFrameUrl = $derived(
        recordingId && keyframeTimestampNs && logTimeNs
            ? getCameraFrameUrl({
                  datasetId,
                  recordingId,
                  channelId,
                  keyframeTimestampNs,
                  logTimeNs
              })
            : null
    );

    let frameUrl = $state<string | null>(null);
    $effect(() => {
        if (!blob) {
            frameUrl = null;
            return;
        }
        const url = URL.createObjectURL(blob);
        frameUrl = url;
        return () => URL.revokeObjectURL(url);
    });

    let failedFrameUrl = $state<string | null>(null);

    // Tile width follows the frame's own aspect ratio; square until the image has loaded.
    let aspectRatio = $state(1);
    let figureHeight = $state(0);
    const CAPTION_HEIGHT_PX = 24;
    const BORDER_PX = 2;
    const tileWidth = $derived(
        Math.max(0, figureHeight - CAPTION_HEIGHT_PX) * aspectRatio + BORDER_PX
    );

    return {
        get frameUrl() {
            return frameUrl;
        },
        get fullFrameUrl() {
            return fullFrameUrl;
        },
        get failedFrameUrl() {
            return failedFrameUrl;
        },
        get tileWidth() {
            return tileWidth;
        },
        get figureHeight() {
            return figureHeight;
        },
        set figureHeight(value) {
            figureHeight = value;
        },
        handleLoad: (event: Event) => {
            const image = event.currentTarget as HTMLImageElement;
            if (image.naturalWidth && image.naturalHeight)
                aspectRatio = image.naturalWidth / image.naturalHeight;
        },
        handleError: () => {
            failedFrameUrl = frameUrl;
        }
    };
}
