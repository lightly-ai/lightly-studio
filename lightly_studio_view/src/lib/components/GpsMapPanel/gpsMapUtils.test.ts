import { describe, expect, it } from 'vitest';
import {
    bboxFromCorners,
    colorForPoint,
    pointInBbox,
    sampleIdsInBbox,
    type GpsPoint,
    type GpsTag
} from './gpsMapUtils';
import { getColorByLabel } from '$lib/utils';
import { UNASSIGNED_COLOR } from '$lib/components/PlotPanel/plotColorUtils';

describe('bboxFromCorners', () => {
    it('normalizes corners regardless of order', () => {
        const bbox = bboxFromCorners({ lat: 47.5, lon: 8.8 }, { lat: 47.0, lon: 8.0 });
        expect(bbox).toEqual({ latMin: 47.0, latMax: 47.5, lonMin: 8.0, lonMax: 8.8 });
    });
});

describe('pointInBbox', () => {
    const bbox = { latMin: 47.0, latMax: 47.5, lonMin: 8.0, lonMax: 8.8 };

    it('includes points inside and on the edges', () => {
        expect(pointInBbox({ lat: 47.2, lon: 8.4 }, bbox)).toBe(true);
        expect(pointInBbox({ lat: 47.0, lon: 8.0 }, bbox)).toBe(true);
    });

    it('excludes points outside', () => {
        expect(pointInBbox({ lat: 46.9, lon: 8.4 }, bbox)).toBe(false);
        expect(pointInBbox({ lat: 47.2, lon: 9.0 }, bbox)).toBe(false);
    });
});

describe('sampleIdsInBbox', () => {
    it('returns only the enclosed sample ids', () => {
        const points: GpsPoint[] = [
            { sampleId: 'a', lat: 47.1, lon: 8.1, tagIds: [] },
            { sampleId: 'b', lat: 40.0, lon: 8.1, tagIds: [] },
            { sampleId: 'c', lat: 47.4, lon: 8.7, tagIds: [] }
        ];
        const bbox = bboxFromCorners({ lat: 47.0, lon: 8.0 }, { lat: 47.5, lon: 8.8 });
        expect(sampleIdsInBbox(points, bbox)).toEqual(['a', 'c']);
    });
});

describe('colorForPoint', () => {
    const tags: GpsTag[] = [
        { tagId: '1', name: 'batch_A' },
        { tagId: '2', name: 'batch_B' }
    ];

    it('colors by the highest-priority matching tag', () => {
        expect(colorForPoint(['2', '1'], tags)).toBe(getColorByLabel('batch_A').color);
    });

    it('falls back to the next tag when the first does not match', () => {
        expect(colorForPoint(['2'], tags)).toBe(getColorByLabel('batch_B').color);
    });

    it('dims points that match no selected tag', () => {
        expect(colorForPoint(['99'], tags)).toBe(UNASSIGNED_COLOR);
        expect(colorForPoint([], tags)).toBe(UNASSIGNED_COLOR);
    });
});
