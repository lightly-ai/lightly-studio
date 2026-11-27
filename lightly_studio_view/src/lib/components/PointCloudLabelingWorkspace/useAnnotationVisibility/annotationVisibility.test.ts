import { describe, expect, it } from 'vitest';
import {
    cuboidToVisibilityRef,
    getTrackVisibilityKey,
    isAnnotationHidden,
    isSelectedCuboidHidden,
    tickAnnotationToVisibilityRef,
    toggleSetEntry
} from './annotationVisibility';

const trackedRef = { annotationId: 'a1', sourceId: 'gt', trackId: 'track-1' };
const untrackedRef = { annotationId: 'a2', sourceId: 'gt', trackId: null };
const nothingHidden = { sourceIds: new Set<string>(), trackKeys: new Set<string>() };

describe('annotationVisibility', () => {
    it('hides every annotation of a hidden source', () => {
        const hidden = { ...nothingHidden, sourceIds: new Set(['gt']) };

        expect(isAnnotationHidden(trackedRef, hidden)).toBe(true);
        expect(isAnnotationHidden(untrackedRef, hidden)).toBe(true);
        expect(isAnnotationHidden({ ...trackedRef, sourceId: 'pred' }, hidden)).toBe(false);
    });

    it('hides an annotation of the same track on another tick', () => {
        const hidden = {
            ...nothingHidden,
            trackKeys: new Set([getTrackVisibilityKey(trackedRef)])
        };

        expect(isAnnotationHidden({ ...trackedRef, annotationId: 'a1-next-tick' }, hidden)).toBe(
            true
        );
    });

    it('hides only the untracked annotation itself', () => {
        const hidden = {
            ...nothingHidden,
            trackKeys: new Set([getTrackVisibilityKey(untrackedRef)])
        };

        expect(isAnnotationHidden(untrackedRef, hidden)).toBe(true);
        expect(isAnnotationHidden({ ...untrackedRef, annotationId: 'a3' }, hidden)).toBe(false);
    });

    it('toggleSetEntry adds a missing key and removes a present one without mutating the input', () => {
        const input = new Set(['a']);

        expect(toggleSetEntry(input, 'b')).toEqual(new Set(['a', 'b']));
        expect(toggleSetEntry(input, 'a')).toEqual(new Set());
        expect(input).toEqual(new Set(['a']));
    });

    it('maps a tick annotation and its cuboid to the same track key', () => {
        const fromTick = tickAnnotationToVisibilityRef({
            sample_id: 'a1',
            annotation_collection_id: 'gt',
            object_track_id: 'track-1'
        });
        const fromCuboid = cuboidToVisibilityRef({
            id: 'a1',
            annotationSourceId: 'gt',
            trackId: 'track-1'
        });

        expect(fromTick).toEqual(fromCuboid);
    });

    it('reports a hidden selection only when the selected cuboid is hidden', () => {
        const cuboids = [{ id: 'a1' }, { id: 'a2' }];
        const isHidden = ({ id }: { id: string }) => id === 'a1';

        expect(isSelectedCuboidHidden('a1', cuboids, isHidden)).toBe(true);
        expect(isSelectedCuboidHidden('a2', cuboids, isHidden)).toBe(false);
        expect(isSelectedCuboidHidden(null, cuboids, isHidden)).toBe(false);
        expect(isSelectedCuboidHidden('missing', cuboids, isHidden)).toBe(false);
    });
});
