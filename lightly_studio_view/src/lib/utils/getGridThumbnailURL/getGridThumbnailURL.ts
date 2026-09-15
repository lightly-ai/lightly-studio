import { PUBLIC_SAMPLES_URL, PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
import { withProxyMediaMode } from '../mediaRecovery';

export type GridThumbnailQuality = 'raw' | 'high';

type GridThumbnailURLParams = {
    baseUrl: string;
    quality: GridThumbnailQuality;
    renderedWidth?: number;
    renderedHeight?: number;
    cacheBuster?: string;
    mode?: 'proxy';
};

export function getGridThumbnailRequestSize(renderedSize: number, devicePixelRatio = 1): number {
    if (renderedSize <= 0) {
        return 0;
    }
    return Math.ceil(renderedSize * Math.min(devicePixelRatio, 2));
}

function buildGridThumbnailURL({
    baseUrl,
    quality,
    renderedWidth,
    renderedHeight,
    cacheBuster,
    mode
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
    const url = queryString ? `${baseUrl}?${queryString}` : baseUrl;
    return mode === 'proxy' ? withProxyMediaMode(url) : url;
}

export function getGridImageURL({
    sampleId,
    quality,
    renderedWidth,
    renderedHeight,
    cacheBuster,
    mode
}: {
    sampleId: string;
    quality: GridThumbnailQuality;
    renderedWidth?: number;
    renderedHeight?: number;
    cacheBuster?: string;
    mode?: 'proxy';
}): string {
    return buildGridThumbnailURL({
        baseUrl: `${PUBLIC_SAMPLES_URL}/sample/${sampleId}`,
        quality,
        renderedWidth,
        renderedHeight,
        cacheBuster,
        mode
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
