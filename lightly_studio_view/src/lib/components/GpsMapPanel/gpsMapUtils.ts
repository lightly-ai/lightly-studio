import { getColorByLabel } from '$lib/utils';
import { UNASSIGNED_COLOR } from '$lib/components/PlotPanel/plotColorUtils';

/** A geographic bounding box in lat/lon degrees. */
export interface Bbox {
    latMin: number;
    latMax: number;
    lonMin: number;
    lonMax: number;
}

/** A GPS point held client-side for selection and coloring. */
export interface GpsPoint {
    sampleId: string;
    lat: number;
    lon: number;
    tagIds: string[];
}

/** A tag the user can color/compare by. */
export interface GpsTag {
    tagId: string;
    name: string;
}

/** Build a normalized bbox from two opposite corners. */
export function bboxFromCorners(
    a: { lat: number; lon: number },
    b: { lat: number; lon: number }
): Bbox {
    return {
        latMin: Math.min(a.lat, b.lat),
        latMax: Math.max(a.lat, b.lat),
        lonMin: Math.min(a.lon, b.lon),
        lonMax: Math.max(a.lon, b.lon)
    };
}

/** Test whether a point falls inside a bbox (inclusive of edges). */
export function pointInBbox(point: { lat: number; lon: number }, bbox: Bbox): boolean {
    return (
        point.lat >= bbox.latMin &&
        point.lat <= bbox.latMax &&
        point.lon >= bbox.lonMin &&
        point.lon <= bbox.lonMax
    );
}

/** Return the sample ids of every point inside the bbox. */
export function sampleIdsInBbox(points: readonly GpsPoint[], bbox: Bbox): string[] {
    return points.filter((point) => pointInBbox(point, bbox)).map((point) => point.sampleId);
}

/**
 * Pick a point's color from the selected tags.
 *
 * The first selected tag (highest priority) the point belongs to wins; points
 * in none of the selected tags are dimmed to {@link UNASSIGNED_COLOR} but kept
 * visible so the full geographic spread still shows. Tag colors reuse the same
 * assignment as the embedding plot so the two views agree.
 */
export function colorForPoint(
    pointTagIds: readonly string[],
    orderedSelectedTags: readonly GpsTag[]
): string {
    const pointTagIdSet = new Set(pointTagIds);
    for (const tag of orderedSelectedTags) {
        if (pointTagIdSet.has(tag.tagId)) {
            return getColorByLabel(tag.name).color;
        }
    }
    return UNASSIGNED_COLOR;
}
