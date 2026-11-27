import type { PolygonInput } from '$lib/workers/maskRendererUtils';

type Rgba = [number, number, number, number];

const POLYGON_FILL_ALPHA = 0.4;
const OPAQUE_ALPHA_BYTE = 255;

export interface PolygonAnnotation {
    annotation_type: 'polygon';
    annotation_label_name: string;
    polygons: Array<Array<[number, number]>>;
    segmentation_mask?: undefined;
    object_detection_details?: undefined;
    color?: undefined;
    opacity?: undefined;
    // If set, color by this source instead of by class.
    sourceName?: string;
}

/** Builds the worker input for a polygon. `resolveColor` gives the color for an alpha. */
export const toPolygonInput = (
    polygons: PolygonAnnotation['polygons'],
    resolveColor: (colorAlpha: number) => Rgba
): PolygonInput => {
    // The custom alpha applies only to the fill, as in the detail view.
    const [r, g, b] = resolveColor(1);
    return {
        // Plain arrays, so postMessage never receives reactive proxies.
        parts: polygons.map((part) => part.map(([x, y]) => [x, y])),
        strokeColor: [r, g, b, OPAQUE_ALPHA_BYTE],
        fillColor: resolveColor(POLYGON_FILL_ALPHA)
    };
};
