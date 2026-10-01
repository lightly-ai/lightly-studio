import { getAnnotation, getVideoById, type AnnotationView } from '$lib/api/lightly_studio_local';
import { getGridFrameURL, getGridImageURL } from '$lib/utils';

const THUMBNAIL_SIZE = 256;

type PlotRoute = 'images' | 'videos' | 'annotations';

export interface Thumbnail {
    url: string;
    annotation?: AnnotationView;
}

export type ThumbnailResolver = (sampleId: string) => Promise<Thumbnail | null>;

async function getVideoThumbnail(videoSampleId: string): Promise<Thumbnail | null> {
    const { data } = await getVideoById({ path: { sample_id: videoSampleId } });
    const frameSampleId = data?.frame?.sample_id;
    if (!frameSampleId) {
        return null;
    }
    return {
        url: getGridFrameURL({
            sampleId: frameSampleId,
            quality: 'high',
            renderedWidth: THUMBNAIL_SIZE,
            renderedHeight: THUMBNAIL_SIZE
        })
    };
}

async function getAnnotationThumbnail(
    annotationSampleId: string,
    collectionId: string,
    cacheBuster?: string
): Promise<Thumbnail | null> {
    const { data } = await getAnnotation({
        path: { collection_id: collectionId, annotation_id: annotationSampleId }
    });
    if (!data?.parent_sample_id) {
        return null;
    }
    return {
        // Crop coordinates use the original sample resolution, so load the raw image.
        url: getImageThumbnailURL(data.parent_sample_id, 'raw', cacheBuster),
        annotation: data
    };
}

function getImageThumbnailURL(
    sampleId: string,
    quality: 'raw' | 'high',
    cacheBuster?: string
): string {
    return getGridImageURL({
        sampleId,
        quality,
        renderedWidth: THUMBNAIL_SIZE,
        renderedHeight: THUMBNAIL_SIZE,
        cacheBuster
    });
}

async function getThumbnail(params: {
    route: PlotRoute;
    sampleId: string;
    collectionId: string;
    cacheBuster?: string;
}): Promise<Thumbnail | null> {
    const { route, sampleId, collectionId, cacheBuster } = params;
    if (route === 'videos') {
        return getVideoThumbnail(sampleId);
    }
    if (route === 'annotations') {
        return getAnnotationThumbnail(sampleId, collectionId, cacheBuster);
    }
    return { url: getImageThumbnailURL(sampleId, 'high', cacheBuster) };
}

/**
 * Builds a resolver that maps a hovered sample ID to a thumbnail URL. Videos
 * and annotations need one extra API lookup (poster frame / parent image) to
 * reach a displayable image, so lookups are cached per sample.
 */
export function createThumbnailResolver(params: {
    route: PlotRoute;
    collectionId: string;
    cacheBuster?: string;
}): ThumbnailResolver {
    const { route, collectionId, cacheBuster } = params;
    const thumbnailBySampleId = new Map<string, Promise<Thumbnail | null>>();
    return (sampleId) => {
        const cached = thumbnailBySampleId.get(sampleId);
        if (cached) {
            return cached;
        }
        const thumbnail = getThumbnail({ route, sampleId, collectionId, cacheBuster }).catch(() => {
            thumbnailBySampleId.delete(sampleId);
            return null;
        });
        thumbnailBySampleId.set(sampleId, thumbnail);
        return thumbnail;
    };
}
