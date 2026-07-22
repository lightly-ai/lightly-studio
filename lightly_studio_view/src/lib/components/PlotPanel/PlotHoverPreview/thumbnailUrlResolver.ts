import { getAnnotation, getVideoById } from '$lib/api/lightly_studio_local';
import { getGridFrameURL, getGridImageURL } from '$lib/utils';

const THUMBNAIL_SIZE = 256;

type PlotRoute = 'images' | 'videos' | 'annotations';

export type ThumbnailUrlResolver = (sampleId: string) => Promise<string | null>;

async function getVideoThumbnailURL(videoSampleId: string): Promise<string | null> {
    const { data } = await getVideoById({ path: { sample_id: videoSampleId } });
    const frameSampleId = data?.frame?.sample_id;
    if (!frameSampleId) {
        return null;
    }
    return getGridFrameURL({
        sampleId: frameSampleId,
        quality: 'high',
        renderedWidth: THUMBNAIL_SIZE,
        renderedHeight: THUMBNAIL_SIZE
    });
}

async function getAnnotationThumbnailURL(
    annotationSampleId: string,
    collectionId: string,
    cacheBuster?: string
): Promise<string | null> {
    const { data } = await getAnnotation({
        path: { collection_id: collectionId, annotation_id: annotationSampleId }
    });
    if (!data?.parent_sample_id) {
        return null;
    }
    return getImageThumbnailURL(data.parent_sample_id, cacheBuster);
}

async function getImageThumbnailURL(
    sampleId: string,
    cacheBuster?: string
): Promise<string | null> {
    return getGridImageURL({
        sampleId,
        quality: 'high',
        renderedWidth: THUMBNAIL_SIZE,
        renderedHeight: THUMBNAIL_SIZE,
        cacheBuster
    });
}

function getThumbnailURL(params: {
    route: PlotRoute;
    sampleId: string;
    collectionId: string;
    cacheBuster?: string;
}): Promise<string | null> {
    const { route, sampleId, collectionId, cacheBuster } = params;
    if (route === 'videos') {
        return getVideoThumbnailURL(sampleId);
    }
    if (route === 'annotations') {
        return getAnnotationThumbnailURL(sampleId, collectionId, cacheBuster);
    }
    return getImageThumbnailURL(sampleId, cacheBuster);
}

/**
 * Builds a resolver that maps a hovered sample ID to a thumbnail URL. Videos
 * and annotations need one extra API lookup (poster frame / parent image) to
 * reach a displayable image, so lookups are cached per sample.
 */
export function createThumbnailUrlResolver(params: {
    route: PlotRoute;
    collectionId: string;
    cacheBuster?: string;
}): ThumbnailUrlResolver {
    const { route, collectionId, cacheBuster } = params;
    const urlBySampleId = new Map<string, Promise<string | null>>();
    return (sampleId) => {
        const cached = urlBySampleId.get(sampleId);
        if (cached) {
            return cached;
        }
        const url = getThumbnailURL({ route, sampleId, collectionId, cacheBuster }).catch(() => {
            urlBySampleId.delete(sampleId);
            return null;
        });
        urlBySampleId.set(sampleId, url);
        return url;
    };
}
