export const GRID_IMAGE_SEARCH_DROP_EVENT = 'lightly:grid-image-search-drop';
export const GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR = '[data-grid-search-drop-target]';
export const DRAG_START_THRESHOLD_PX = 8;
/**
 * Marks a control inside a tile that must not start a drag.
 *
 * Dragging captures the pointer on the tile, and a captured pointer retargets the following
 * click to the capturing element — so without this a click on the tile's checkbox would arrive
 * at the tile and open the sample instead of selecting it.
 */
export const GRID_ITEM_NO_DRAG_SELECTOR = '[data-grid-item-no-drag]';
export const DRAG_PREVIEW_OFFSET_PX = 14;

export type GridItemDragData = {
    url: string;
    fileName: string;
    /** When set, drag-to-search uses the stored annotation embedding instead of re-embedding the crop. */
    annotationSampleId?: string;
    /** Annotation collection that owns the stored embedding (child collection, not the parent image collection). */
    annotationCollectionId?: string;
};
