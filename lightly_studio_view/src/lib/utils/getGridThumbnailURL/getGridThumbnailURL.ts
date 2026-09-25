import { PUBLIC_SAMPLES_URL, PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';

export type GridThumbnailQuality = 'raw' | 'high';

type GridThumbnailURLParams = {
    baseUrl: string;
    quality: GridThumbnailQuality;
    renderedWidth?: number;
    renderedHeight?: number;
    cacheBuster?: string;
};

// Fixed request sizes keep thumbnail URLs stable while the grid resizes, so the
// browser cache serves them instead of sending a new request for every pixel.
const GRID_THUMBNAIL_SIZE_STEPS = [128, 192, 256, 384, 512, 768, 1024, 1536, 2048];

export function getGridThumbnailRequestSize(renderedSize: number, devicePixelRatio = 1): number {
    if (renderedSize <= 0) {
        return 0;
    }
    const size = Math.ceil(renderedSize * Math.min(devicePixelRatio, 2));
    return (
        GRID_THUMBNAIL_SIZE_STEPS.find((step) => step >= size) ??
        GRID_THUMBNAIL_SIZE_STEPS[GRID_THUMBNAIL_SIZE_STEPS.length - 1]
    );
}

function buildGridThumbnailURL({
    baseUrl,
    quality,
    renderedWidth,
    renderedHeight,
    cacheBuster
}: GridThumbnailURLParams): string {
    const params = new URLSearchParams();

    if (cacheBuster) {
        params.set('v', cacheBuster);
    }

    if (quality === 'high') {
        params.set('quality', 'high');
        if (renderedWidth && renderedWidth > 0) {
            params.set('max_width', String(renderedWidth));
        }
        if (renderedHeight && renderedHeight > 0) {
            params.set('max_height', String(renderedHeight));
        }
    }

    const queryString = params.toString();
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
}

export function getGridImageURL({
    sampleId,
    quality,
    renderedWidth,
    renderedHeight,
    cacheBuster
}: {
    sampleId: string;
    quality: GridThumbnailQuality;
    renderedWidth?: number;
    renderedHeight?: number;
    cacheBuster?: string;
}): string {
    return buildGridThumbnailURL({
        baseUrl: `${PUBLIC_SAMPLES_URL}/sample/${sampleId}`,
        quality,
        renderedWidth,
        renderedHeight,
        cacheBuster
    });
}

export function getGridFrameURL({
    sampleId,
    quality,
    renderedWidth,
    renderedHeight
}: {
    sampleId: string;
    quality: GridThumbnailQuality;
    renderedWidth?: number;
    renderedHeight?: number;
}): string {
    return buildGridThumbnailURL({
        baseUrl: `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sampleId}`,
        quality,
        renderedWidth,
        renderedHeight
    });
}
