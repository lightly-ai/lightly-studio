interface PreloadAdjacentImagesParams {
    nextSampleId: string | null | undefined;
    previousSampleId: string | null | undefined;
    /** Number of images to preload after the current one, including `nextSampleId`. */
    nextCount: number;
    /** Returns the sample after `sampleId` in the current order. */
    getNextSampleId: (sampleId: string) => Promise<string | null | undefined>;
    preloadImage: (sampleId: string) => void;
    /** Stops the walk, for example when the user moved to another sample. */
    isCancelled: () => boolean;
}

/**
 * Preloads the images around the current sample, so stepping with next/previous shows them
 * at once. The next image goes first, then the previous one, then the ones after the next.
 */
export async function preloadAdjacentImages({
    nextSampleId,
    previousSampleId,
    nextCount,
    getNextSampleId,
    preloadImage,
    isCancelled
}: PreloadAdjacentImagesParams): Promise<void> {
    if (nextSampleId) preloadImage(nextSampleId);
    if (previousSampleId) preloadImage(previousSampleId);

    let sampleId = nextSampleId;
    for (let index = 1; index < nextCount && sampleId; index++) {
        try {
            sampleId = await getNextSampleId(sampleId);
        } catch {
            return;
        }
        if (isCancelled()) return;
        if (sampleId) preloadImage(sampleId);
    }
}

// Holds the image objects until they load, so the requests are not dropped early.
const loadingImages = new Set<HTMLImageElement>();

/** Starts loading `url` into the browser cache. */
export function preloadImageUrl(url: string): void {
    const image = new Image();
    const release = () => loadingImages.delete(image);
    image.onload = release;
    image.onerror = release;
    loadingImages.add(image);
    image.src = url;
}
