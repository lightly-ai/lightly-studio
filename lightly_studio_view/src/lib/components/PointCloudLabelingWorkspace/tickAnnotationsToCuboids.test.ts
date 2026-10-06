import type { AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import { describe, expect, it, vi } from 'vitest';
import { tickAnnotationsToClasses, tickAnnotationsToCuboids } from './tickAnnotationsToCuboids';

const createAnnotation = (overrides: Partial<AnnotationView> = {}): AnnotationView => ({
    parent_sample_id: 'tick-1',
    sample_id: 'annotation-1',
    annotation_collection_id: 'source-1',
    annotation_type: 'cuboid_3d',
    annotation_label: { annotation_label_name: 'car' },
    created_at: new Date('2025-01-01T00:00:00Z'),
    cuboid_3d_details: {
        frame_id: 'map',
        px: 1,
        py: 2,
        pz: 3,
        qx: 0,
        qy: 0,
        qz: 0,
        qw: 1,
        sx: 4,
        sy: 5,
        sz: 6
    },
    ...overrides
});

describe('tickAnnotationsToCuboids', () => {
    it('maps every cuboid in the tick', () => {
        const annotations = [
            createAnnotation({ object_track_id: 'track-1', object_track_number: 7 }),
            createAnnotation({
                sample_id: 'annotation-2',
                cuboid_3d_details: { ...createAnnotation().cuboid_3d_details!, frame_id: 'lidar' }
            }),
            createAnnotation({ sample_id: 'image-annotation', cuboid_3d_details: null })
        ];

        expect(tickAnnotationsToCuboids(annotations)).toEqual([
            {
                id: 'annotation-1',
                frameId: 'map',
                coordinateFrame: {
                    id: 'map',
                    convention: 'right-handed-x-forward-y-left-z-up',
                    unit: 'meter'
                },
                annotationClassId: 'car',
                annotationSourceId: 'source-1',
                trackId: 'track-1',
                trackNumber: 7,
                parentTrackNumber: null,
                keyframeId: null,
                center: [1, 2, 3],
                size: [4, 5, 6],
                rotation: [0, 0, 0, 1]
            },
            {
                id: 'annotation-2',
                frameId: 'lidar',
                coordinateFrame: {
                    id: 'lidar',
                    convention: 'right-handed-x-forward-y-left-z-up',
                    unit: 'meter'
                },
                annotationClassId: 'car',
                annotationSourceId: 'source-1',
                trackId: null,
                trackNumber: null,
                parentTrackNumber: null,
                keyframeId: null,
                center: [1, 2, 3],
                size: [4, 5, 6],
                rotation: [0, 0, 0, 1]
            }
        ]);
    });

    it('maps parentTrackNumber from parent_object_track_number', () => {
        const annotations = [
            createAnnotation({ object_track_id: 'track-2', parent_object_track_number: 3 }),
            createAnnotation({ sample_id: 'annotation-2' })
        ];

        const cuboids = tickAnnotationsToCuboids(annotations);

        expect(cuboids[0]).toMatchObject({ trackId: 'track-2', trackNumber: null, parentTrackNumber: 3 });
        expect(cuboids[1]).toMatchObject({ parentTrackNumber: null });
    });

    it('keeps tick cuboids when their frame differs from the displayed frame', () => {
        const annotations = [
            createAnnotation(),
            createAnnotation({
                sample_id: 'annotation-2',
                cuboid_3d_details: { ...createAnnotation().cuboid_3d_details!, frame_id: 'lidar' }
            })
        ];

        expect(tickAnnotationsToCuboids(annotations).map(({ id }) => id)).toEqual([
            'annotation-1',
            'annotation-2'
        ]);
        expect(tickAnnotationsToCuboids([])).toEqual([]);
    });
});

describe('tickAnnotationsToClasses', () => {
    it('deduplicates tick labels across frames and injects colors', () => {
        const annotations = [
            createAnnotation(),
            createAnnotation({ sample_id: 'annotation-2' }),
            createAnnotation({
                sample_id: 'annotation-3',
                annotation_label: { annotation_label_name: 'truck' },
                cuboid_3d_details: { ...createAnnotation().cuboid_3d_details!, frame_id: 'lidar' }
            })
        ];
        const getColor = vi.fn((name: string) => `${name}-color`);

        expect(tickAnnotationsToClasses(annotations, getColor)).toEqual([
            { id: 'car', name: 'car', color: 'car-color' },
            { id: 'truck', name: 'truck', color: 'truck-color' }
        ]);
        expect(getColor).toHaveBeenCalledTimes(2);
        expect(tickAnnotationsToClasses(annotations, getColor)).toEqual([
            { id: 'car', name: 'car', color: 'car-color' },
            { id: 'truck', name: 'truck', color: 'truck-color' }
        ]);
    });
});
