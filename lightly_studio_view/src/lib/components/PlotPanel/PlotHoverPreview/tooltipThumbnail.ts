import { getAnnotation, getVideoById } from '$lib/api/lightly_studio_local';
import { getGridFrameURL, getGridImageURL } from '$lib/utils';
import { HIDDEN_CATEGORY } from '../plotCategories';

// Requested at 256px so the backend downsizes the media; small enough to load
// fast while the user sweeps across points.
const THUMBNAIL_SIZE = 256;

// Hover hit radius in screen pixels; querySelection receives the data-domain
// size of one pixel so the radius scales with zoom.
const HOVER_RADIUS_PX = 10;

type PlotRoute = 'images' | 'videos' | 'annotations';

interface CreateQuerySelectionParams {
    x: Float32Array | undefined;
    y: Float32Array | undefined;
    sampleIds: string[] | undefined;
    /** Final per-point plot categories; points in HIDDEN_CATEGORY are not hoverable. */
    category: Uint8Array | undefined;
}

interface TooltipDataPoint {
    x: number;
    y: number;
    category?: number;
    identifier: string;
}

/**
 * Builds the `querySelection` callback for the embedding view: given a hover
 * location it returns the nearest visible point, or null when none is within
 * the hover radius. The plain (array-based) EmbeddingView only emits hover
 * tooltips when this callback is provided; the returned point carries the
 * sample ID as `identifier`.
 */
export function createQuerySelection(params: CreateQuerySelectionParams) {
    const { x, y, sampleIds, category } = params;
    return async (queryX: number, queryY: number, unitDistance: number) => {
        if (!x || !y || !sampleIds) {
            return null;
        }
        const maxDistance = HOVER_RADIUS_PX * unitDistance;
        let nearestIndex = -1;
        let nearestDistanceSq = maxDistance * maxDistance;
        for (let index = 0; index < x.length; index++) {
            if (category && category[index] === HIDDEN_CATEGORY) {
                continue;
            }
            const dx = x[index] - queryX;
            const dy = y[index] - queryY;
            const distanceSq = dx * dx + dy * dy;
            if (distanceSq < nearestDistanceSq) {
                nearestDistanceSq = distanceSq;
                nearestIndex = index;
            }
        }
        if (nearestIndex === -1) {
            return null;
        }
        const point: TooltipDataPoint = {
            x: x[nearestIndex],
            y: y[nearestIndex],
            category: category?.[nearestIndex],
            identifier: sampleIds[nearestIndex]
        };
        return point;
    };
}

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

// Shows the annotation's parent image; cropping to the annotation can follow later.
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
        const url = (
            route === 'videos'
                ? getVideoThumbnailURL(sampleId)
                : route === 'annotations'
                  ? getAnnotationThumbnailURL(sampleId, collectionId, cacheBuster)
                  : getImageThumbnailURL(sampleId, cacheBuster)
        ).catch(() => null);
        urlBySampleId.set(sampleId, url);
        return url;
    };
}
