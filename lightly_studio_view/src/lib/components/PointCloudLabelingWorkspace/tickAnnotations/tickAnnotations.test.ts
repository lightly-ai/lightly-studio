import { describe, expect, it } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import { toAnnotationClasses, toCuboidAnnotations } from './tickAnnotations';

const cuboidDetails = {
    frame_id: 'odom',
    px: 1,
    py: 2,
    pz: 3,
    qx: 0,
    qy: 0,
    qz: 0,
    qw: 2,
    sx: 4,
    sy: 2,
    sz: 1
};

const createAnnotation = (overrides: Partial<AnnotationView> = {}): AnnotationView => ({
    parent_sample_id: 'tick-1',
    sample_id: 'annotation-1',
    annotation_collection_id: 'collection-1',
    annotation_type: 'cuboid_3d' as AnnotationView['annotation_type'],
    annotation_label: { annotation_label_name: 'truck' },
    created_at: new Date(0),
    cuboid_3d_details: cuboidDetails,
    object_track_id: 'track-1',
    ...overrides
});

describe('toCuboidAnnotations', () => {
    it('maps cuboid details into a cuboid with a normalized rotation', () => {
        expect(toCuboidAnnotations([createAnnotation()])).toEqual([
            {
                id: 'annotation-1',
                frameId: 'odom',
                coordinateFrame: {
                    id: 'odom',
                    convention: 'right-handed-x-forward-y-left-z-up',
                    unit: 'meter'
                },
                annotationClassId: 'truck',
                annotationSourceId: 'collection-1',
                trackId: 'track-1',
                keyframeId: null,
                center: [1, 2, 3],
                size: [4, 2, 1],
                rotation: [0, 0, 0, 1]
            }
        ]);
    });

    it('skips annotations without cuboid details and invalid cuboids', () => {
        const annotations = [
            createAnnotation({ sample_id: 'box-2d', cuboid_3d_details: null }),
            createAnnotation({ sample_id: 'flat', cuboid_3d_details: { ...cuboidDetails, sz: 0 } }),
            createAnnotation({ sample_id: 'valid' })
        ];
        expect(toCuboidAnnotations(annotations).map((cuboid) => cuboid.id)).toEqual(['valid']);
    });
});

describe('toAnnotationClasses', () => {
    it('creates one colored class per label name in order of first use', () => {
        const cuboids = toCuboidAnnotations([
            createAnnotation({
                sample_id: 'a',
                annotation_label: { annotation_label_name: 'car' }
            }),
            createAnnotation({
                sample_id: 'b',
                annotation_label: { annotation_label_name: 'bus' }
            }),
            createAnnotation({ sample_id: 'c', annotation_label: { annotation_label_name: 'car' } })
        ]);
        const classes = toAnnotationClasses(cuboids);
        expect(classes.map(({ id, name }) => ({ id, name }))).toEqual([
            { id: 'car', name: 'car' },
            { id: 'bus', name: 'bus' }
        ]);
        classes.forEach(({ color }) => expect(color).toMatch(/^#[0-9a-f]{6}$/));
    });
});
