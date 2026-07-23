import type { DataPoint, OverlayProxy } from 'embedding-atlas/svelte';

import { getPreviewPosition } from './previewPosition';

interface GetHoverPreviewStateParams {
    tooltip: DataPoint | null;
    /** The preview is hidden while a lasso selection is being drawn. */
    rangeSelectionActive: boolean;
    proxy: OverlayProxy | null;
    cardSize: number;
}

/**
 * Derives what the hover preview should show: the hovered sample and the card
 * position (directly above the point), or null when nothing should be shown.
 */
export function getHoverPreviewState({
    tooltip,
    rangeSelectionActive,
    proxy,
    cardSize
}: GetHoverPreviewStateParams): { sampleId: string; left: number; top: number } | null {
    if (tooltip === null || rangeSelectionActive || proxy === null) {
        return null;
    }
    if (typeof tooltip.identifier !== 'string') {
        return null;
    }
    const point = proxy.location(tooltip.x, tooltip.y);
    const position = getPreviewPosition({ point, plotWidth: proxy.width, cardSize });
    if (position === null) {
        return null;
    }
    return {
        sampleId: tooltip.identifier,
        ...position
    };
}
