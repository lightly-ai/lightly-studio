import type { ExportImagesEstimateResponse } from '$lib/api/lightly_studio_local';

/**
 * Largest export with images offered as a browser download. The server zips the images before
 * sending them, so bigger exports wait long and can time out; the code export writes the images
 * straight to the user's disk instead. A first guess, to check against hosted timings.
 */
export const MAX_BROWSER_DOWNLOAD_BYTES = 2 * 1024 ** 3;

export const TOO_LARGE_REASON =
    'Too large to download in the browser. Use Copy as code; it writes the images straight to your disk.';

interface IncludeImagesState {
    /** Whether the images can be added to the browser download. */
    allowed: boolean;
    /** The image count and estimated size, or undefined while the estimate loads. */
    sizeText: string | undefined;
    /** Why the images can't be added. Set only when `allowed` is false. */
    reason?: string;
}

/** Formats a byte count with one unit, e.g. "380 MB" or "1.9 GB". */
export function formatBytes(bytes: number): string {
    const units = ['KB', 'MB', 'GB', 'TB'];
    let value = bytes / 1024;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit += 1;
    }
    const rounded = value >= 10 || unit < 2 ? Math.max(1, Math.round(value)) : value.toFixed(1);
    return `${String(rounded).replace(/\.0$/, '')} ${units[unit]}`;
}

/** Decides whether to offer "Include images" for the estimated export size. */
export function getIncludeImagesState(
    estimate: ExportImagesEstimateResponse | undefined
): IncludeImagesState {
    if (!estimate) return { allowed: true, sizeText: undefined };
    const count = `${estimate.image_count.toLocaleString('en-US')} images`;
    if (estimate.estimated_bytes == null) return { allowed: true, sizeText: count };
    const sizeText = `${count}, about ${formatBytes(estimate.estimated_bytes)}`;
    if (estimate.estimated_bytes > MAX_BROWSER_DOWNLOAD_BYTES) {
        return { allowed: false, sizeText, reason: TOO_LARGE_REASON };
    }
    return { allowed: true, sizeText };
}
