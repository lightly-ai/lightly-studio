import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';
import type { GridType } from '$lib/types';
import {
    getGridFrameURL,
    getGridImageURL
} from '$lib/utils/getGridThumbnailURL/getGridThumbnailURL';

const MAX_THUMBNAILS = 3;

/** True when keys typed now belong to a text field, not to the grid. */
export function isTyping(target: EventTarget | null): boolean {
    const element = target instanceof HTMLElement ? target : null;
    return (
        element !== null &&
        (element.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName))
    );
}

/** "Select all N" shows for an ID selection that holds fewer items than the grid. */
export function canOfferSelectAll(
    target: SelectionTarget,
    selectedCount: number,
    gridTotal: number
): boolean {
    return target.kind === 'ids' && gridTotal > selectedCount;
}

/**
 * Thumbnail URLs for the first selected items. Grids without a plain sample thumbnail
 * (annotation crops, videos, captions) get none.
 */
export function getSelectionThumbnailURLs(gridType: GridType, ids: Iterable<string>): string[] {
    const first = [...ids].slice(0, MAX_THUMBNAILS);
    if (gridType === 'images') {
        return first.map((sampleId) => getGridImageURL({ sampleId, quality: 'raw' }));
    }
    if (gridType === 'video_frames') {
        return first.map((sampleId) => getGridFrameURL({ sampleId, quality: 'raw' }));
    }
    return [];
}
