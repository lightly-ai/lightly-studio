export const GRID_IMAGE_SEARCH_DROP_EVENT = 'lightly:grid-image-search-drop';
export const GRID_IMAGE_SEARCH_DROP_TARGET_SELECTOR = '[data-grid-search-drop-target]';
export const DRAG_START_THRESHOLD_PX = 8;
export const DRAG_PREVIEW_OFFSET_PX = 14;

export type GridItemDragData = {
    url: string;
    fileName: string;
};
