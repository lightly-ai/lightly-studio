import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { GridItemDragData } from '$lib/components/GridItem';
import type { CropWindow } from './AnnotationItem/renderCropObjectUrl';

/**
 * Build the drag-to-search payload for an annotation tile.
 *
 * Returns `undefined` until the tile has reported its crop geometry, so dragging
 * is disabled before the tile is ready. `url` is only the drag preview thumbnail:
 * the parent thumbnail until the crop blob is rendered on drag start, then the
 * crop itself. The actual search uses the stored embedding looked up on drop via
 * `annotationSampleId`/`annotationCollectionId`.
 */
export function buildAnnotationDragData(
    annotation: AnnotationView,
    cropWindow: CropWindow | undefined,
    cropUrl: string | undefined
): GridItemDragData | undefined {
    if (!cropWindow) return undefined;
    return {
        url: cropUrl ?? cropWindow.sourceUrl,
        fileName: `${annotation.annotation_label.annotation_label_name}-crop.png`,
        annotationSampleId: annotation.sample_id,
        annotationCollectionId: annotation.annotation_collection_id
    };
}
