import { describe, expect, it } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import {
    areAllLocked,
    isAnnotationLockable,
    listLockableIds,
    toggleLocks
} from './annotationLocks';

describe('isAnnotationLockable', () => {
    it('is true for annotations that show a row lock', () => {
        expect(isAnnotationLockable({ annotation_type: AnnotationType.SEGMENTATION_MASK })).toBe(
            true
        );
        expect(isAnnotationLockable({ annotation_type: AnnotationType.POLYGON })).toBe(true);
    });

    it('is false for object detection and classification annotations', () => {
        expect(isAnnotationLockable({ annotation_type: AnnotationType.OBJECT_DETECTION })).toBe(
            false
        );
        expect(isAnnotationLockable({ annotation_type: AnnotationType.CLASSIFICATION })).toBe(
            false
        );
    });
});

describe('listLockableIds', () => {
    it('lists the ids of lockable annotations only', () => {
        expect(
            listLockableIds([
                { sample_id: 'mask-1', annotation_type: AnnotationType.SEGMENTATION_MASK },
                { sample_id: 'box-1', annotation_type: AnnotationType.OBJECT_DETECTION },
                { sample_id: 'mask-2', annotation_type: AnnotationType.SEGMENTATION_MASK }
            ])
        ).toEqual(['mask-1', 'mask-2']);
    });
});

describe('areAllLocked', () => {
    it('is true when every id is locked', () => {
        expect(areAllLocked(['a', 'b'], new Set(['a', 'b', 'c']))).toBe(true);
    });

    it('is false when some ids are not locked', () => {
        expect(areAllLocked(['a', 'b'], new Set(['a']))).toBe(false);
    });

    it('is false for an empty scope', () => {
        expect(areAllLocked([], new Set(['a']))).toBe(false);
    });
});

describe('toggleLocks', () => {
    it('unlocks all ids when all are locked', () => {
        expect(toggleLocks(['a', 'b'], new Set(['a', 'b', 'other']))).toEqual({
            lockedIds: new Set(['other']),
            locked: false,
            count: 2
        });
    });

    it('locks the unlocked ids when some are locked', () => {
        expect(toggleLocks(['a', 'b', 'c'], new Set(['a']))).toEqual({
            lockedIds: new Set(['a', 'b', 'c']),
            locked: true,
            count: 2
        });
    });

    it('locks all ids when none are locked', () => {
        expect(toggleLocks(['a', 'b'], new Set(['other']))).toEqual({
            lockedIds: new Set(['other', 'a', 'b']),
            locked: true,
            count: 2
        });
    });

    it('changes nothing for an empty scope', () => {
        expect(toggleLocks([], new Set(['other']))).toEqual({
            lockedIds: new Set(['other']),
            locked: true,
            count: 0
        });
    });
});
