/**
 * Holds the decoded camera pictures of the last few frames, and closes the rest.
 *
 * A decoded picture is memory the garbage collector does not manage, so something has to
 * decide when one is no longer on screen. Frames are what a viewer moves between, so that is
 * what this keeps: the newest few frames' pictures stay, the ones behind them are closed. A
 * frame that outlives its pictures still renders -- its cameras simply have nothing to draw,
 * which is the same state as a camera that published no picture for that moment.
 */
export function createCameraImageStore(frameCapacity: number) {
    /** Insertion-ordered by frame, which is what makes the oldest one the first key. */
    const byFrame = new Map<string, Map<string, ImageBitmap>>();

    function add(
        frameId: string,
        images: readonly { resourceId: string; bitmap: ImageBitmap }[]
    ): void {
        if (images.length === 0) return;
        release(frameId);
        byFrame.set(frameId, new Map(images.map((image) => [image.resourceId, image.bitmap])));
        while (byFrame.size > frameCapacity) {
            const oldest = byFrame.keys().next();
            if (oldest.done) break;
            release(oldest.value);
        }
    }

    function get(resourceId: string): ImageBitmap | undefined {
        for (const images of byFrame.values()) {
            const found = images.get(resourceId);
            if (found) return found;
        }
        return undefined;
    }

    function release(frameId: string): void {
        byFrame.get(frameId)?.forEach((bitmap) => bitmap.close());
        byFrame.delete(frameId);
    }

    return {
        add,
        get,
        clear: () => [...byFrame.keys()].forEach(release),
        get size() {
            return byFrame.size;
        }
    };
}
