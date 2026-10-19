import { describe, expect, it } from 'vitest';
import { createPendingSizesTracker } from './cuboidPendingSizes';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

const BASE_ANNOTATION: CuboidAnnotation = {
    id: 'ann-1',
    frameId: 'frame-1',
    coordinateFrame: {
        id: 'ego',
        convention: 'right-handed-x-forward-y-left-z-up',
        unit: 'meter'
    },
    annotationClassId: 'class-1',
    annotationSourceId: 'source-1',
    trackId: null,
    trackNumber: null,
    parentTrackNumber: null,
    keyframeId: null,
    center: [0, 0, 0],
    size: [2, 3, 4],
    rotation: [0, 0, 0, 1]
};

describe('createPendingSizesTracker', () => {
    it('returns undefined for an unknown annotation', () => {
        const tracker = createPendingSizesTracker();

        expect(tracker.get('unknown')).toBeUndefined();
    });

    it('stores and retrieves a pending size', () => {
        const tracker = createPendingSizesTracker();

        tracker.set('ann-1', [10, 20, 30]);

        expect(tracker.get('ann-1')).toEqual([10, 20, 30]);
    });

    it('deletes a pending size by id', () => {
        const tracker = createPendingSizesTracker();
        tracker.set('ann-1', [10, 20, 30]);

        tracker.delete('ann-1');

        expect(tracker.get('ann-1')).toBeUndefined();
    });

    it('removes an entry when the server cuboid matches the pending size', () => {
        const tracker = createPendingSizesTracker();
        tracker.set('ann-1', [2, 3, 4]);

        tracker.reconcile([BASE_ANNOTATION]);

        expect(tracker.get('ann-1')).toBeUndefined();
    });

    it('keeps an entry when the server cuboid has a different size', () => {
        const tracker = createPendingSizesTracker();
        tracker.set('ann-1', [10, 20, 30]);

        tracker.reconcile([BASE_ANNOTATION]);

        expect(tracker.get('ann-1')).toEqual([10, 20, 30]);
    });

    it('removes an entry when the cuboid is no longer present', () => {
        const tracker = createPendingSizesTracker();
        tracker.set('ann-1', [10, 20, 30]);

        tracker.reconcile([]);

        expect(tracker.get('ann-1')).toBeUndefined();
    });

    it('handles multiple cuboids independently', () => {
        const tracker = createPendingSizesTracker();
        const ann2: CuboidAnnotation = { ...BASE_ANNOTATION, id: 'ann-2', size: [5, 5, 5] };
        tracker.set('ann-1', [2, 3, 4]); // matches BASE_ANNOTATION
        tracker.set('ann-2', [99, 99, 99]); // does not match ann2

        tracker.reconcile([BASE_ANNOTATION, ann2]);

        expect(tracker.get('ann-1')).toBeUndefined();
        expect(tracker.get('ann-2')).toEqual([99, 99, 99]);
    });
});
