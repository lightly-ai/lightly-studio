import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { GridItemDragData } from '$lib/components/GridItem';
import type { CropWindow } from './AnnotationItem/renderCropObjectUrl';

interface AnnotationDragDataParams {
    annotation: AnnotationView;
    cropWindow: CropWindow | undefined;
    cropUrl: string | undefined;
}

/**
 * Build the drag-to-search payload for an annotation tile.
 *
 * Returns `undefined` until the tile has reported its crop geometry, so dragging
 * is disabled before the tile is ready. `url` is only the drag preview thumbnail:
 * the parent thumbnail until the crop blob is rendered on drag start, then the
 * crop itself. The actual search uses the stored embedding looked up on drop via
 * `annotationSampleId`/`annotationCollectionId`.
 */
export function buildAnnotationDragData({
    annotation,
    cropWindow,
    cropUrl
}: AnnotationDragDataParams): GridItemDragData | undefined {
    if (!cropWindow) return undefined;
    return {
        url: cropUrl ?? cropWindow.sourceUrl,
        fileName: `${annotation.annotation_label.annotation_label_name}-crop.png`,
        annotationSampleId: annotation.sample_id,
        annotationCollectionId: annotation.annotation_collection_id
    };
}

/**
 * Build drag-to-search payload for a classification annotation tile.
 *
 * Intentionally omits `annotationSampleId` — classification annotations have no
 * per-annotation crop embedding, so `readAnnotationEmbedding` would fail. Omitting it
 * makes the drop handler fall through to the image-upload search path (`search.setImage`),
 * which sends the thumbnail as the query image.
 */
export function buildClassificationDragData({
    annotation,
    cropWindow,
    cropUrl
}: AnnotationDragDataParams): GridItemDragData | undefined {
    if (!cropWindow) return undefined;
    return {
        url: cropUrl ?? cropWindow.sourceUrl,
        fileName: `${annotation.annotation_label.annotation_label_name}-crop.png`
    };
}
