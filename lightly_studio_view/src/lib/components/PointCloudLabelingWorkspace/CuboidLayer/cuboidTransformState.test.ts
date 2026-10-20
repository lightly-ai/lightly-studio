import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { createCuboidTransformState } from './cuboidTransformState';

const ANNOTATION_A: CuboidAnnotation = {
    id: 'ann-a',
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

const ANNOTATION_B: CuboidAnnotation = {
    id: 'ann-b',
    frameId: 'frame-1',
    coordinateFrame: {
        id: 'ego',
        convention: 'right-handed-x-forward-y-left-z-up',
        unit: 'meter'
    },
    annotationClassId: 'class-2',
    annotationSourceId: 'source-1',
    trackId: null,
    trackNumber: null,
    parentTrackNumber: null,
    keyframeId: null,
    center: [5, 5, 5],
    size: [1, 1, 1],
    rotation: [0, 0, 0, 1]
};

describe('createCuboidTransformState', () => {
    it('emits source annotations after reconcile', () => {
        const state = createCuboidTransformState({ onTransform: () => undefined });

        state.reconcile([ANNOTATION_A, ANNOTATION_B]);

        expect(get(state.annotations)).toEqual([ANNOTATION_A, ANNOTATION_B]);
    });

    it('overlays committed transform on the source annotation', async () => {
        const onTransform = vi.fn().mockResolvedValue(true);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);

        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        const result = get(state.annotations);
        expect(result[0].center).toEqual([1, 2, 3]);
        expect(result[0].size).toEqual([10, 20, 30]);
        expect(result[0].annotationClassId).toBe('class-1');
    });

    it('clears overlay once source catches up to the committed values', async () => {
        const onTransform = vi.fn().mockResolvedValue(true);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);
        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        state.reconcile([{ ...ANNOTATION_A, center: [1, 2, 3], size: [10, 20, 30] }]);

        const result = get(state.annotations);
        expect(result[0].center).toEqual([1, 2, 3]);
        expect(result[0].size).toEqual([10, 20, 30]);
    });

    it('keeps overlay while source has not caught up yet', async () => {
        const onTransform = vi.fn().mockResolvedValue(true);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);
        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        state.reconcile([ANNOTATION_A]);

        const result = get(state.annotations);
        expect(result[0].center).toEqual([1, 2, 3]);
        expect(result[0].size).toEqual([10, 20, 30]);
    });

    it('removes overlay when the annotation disappears from source', async () => {
        const onTransform = vi.fn().mockResolvedValue(true);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);
        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        state.reconcile([]);

        expect(get(state.annotations)).toEqual([]);
    });

    it('removes overlay on failed commit', async () => {
        const onTransform = vi.fn().mockResolvedValue(false);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);

        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });
        state.reconcile([ANNOTATION_A]);

        expect(get(state.annotations)[0].center).toEqual([0, 0, 0]);
    });

    it('removes overlay when onTransform throws', async () => {
        const onTransform = vi.fn().mockRejectedValue(new Error('network'));
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);

        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });
        state.reconcile([ANNOTATION_A]);

        expect(get(state.annotations)[0].center).toEqual([0, 0, 0]);
    });

    it('ignores commit for an unknown annotation id', async () => {
        const onTransform = vi.fn();
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A]);

        await state.commit({
            annotationId: 'unknown',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        expect(onTransform).not.toHaveBeenCalled();
        expect(get(state.annotations)).toEqual([ANNOTATION_A]);
    });

    it('begin + cancel reverts to source values', () => {
        const state = createCuboidTransformState({ onTransform: () => undefined });
        state.reconcile([ANNOTATION_A]);

        state.begin(ANNOTATION_A);
        state.cancel('ann-a');

        expect(get(state.annotations)[0].center).toEqual([0, 0, 0]);
    });

    it('does not overlay source during an active drag (begin without commit)', () => {
        const state = createCuboidTransformState({ onTransform: () => undefined });
        state.reconcile([ANNOTATION_A]);

        state.begin(ANNOTATION_A);
        state.reconcile([{ ...ANNOTATION_A, center: [9, 9, 9] }]);

        expect(get(state.annotations)[0].center).toEqual([0, 0, 0]);
    });

    it('handles multiple annotations independently', async () => {
        const onTransform = vi.fn().mockResolvedValue(true);
        const state = createCuboidTransformState({ onTransform });
        state.reconcile([ANNOTATION_A, ANNOTATION_B]);

        await state.commit({
            annotationId: 'ann-a',
            frameId: 'frame-1',
            center: [1, 2, 3],
            rotation: [0, 0, 0, 1],
            size: [10, 20, 30]
        });

        const result = get(state.annotations);
        expect(result[0].center).toEqual([1, 2, 3]);
        expect(result[1].center).toEqual([5, 5, 5]);
    });
});
