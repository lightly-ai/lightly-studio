import { describe, expect, it } from 'vitest';
import { toTimelineTracks } from './toTimelineTracks';
import { createAnnotationFixture, createWorkspaceFixture } from '../domain/fixtures';
import type { CuboidAnnotation } from '../domain';

const FRAME_POSITIONS = new Map([
    ['frame-0', 0],
    ['frame-1', 1],
    ['frame-2', 2]
]);

describe('toTimelineTracks', () => {
    it('places the authored keyframe and its annotation at the matching frame position', () => {
        const { track } = createWorkspaceFixture();
        const annotation = createAnnotationFixture();

        const [result] = toTimelineTracks({
            tracks: [track],
            annotations: [annotation],
            framePositionById: FRAME_POSITIONS
        });

        expect(result.id).toBe(track.id);
        expect(result.keyframes).toEqual([{ id: 'keyframe-0', framePosition: 0 }]);
        expect(result.presentFramePositions).toEqual([0]);
    });

    it('resolves the label and color from the class maps, falling back to the track ID', () => {
        const { track } = createWorkspaceFixture();

        const [withMaps] = toTimelineTracks({
            tracks: [track],
            annotations: [],
            framePositionById: FRAME_POSITIONS,
            classNameById: new Map([[track.annotationClassId, 'Vehicle']]),
            classColorById: new Map([[track.annotationClassId, '#3366ff']])
        });
        const [withoutMaps] = toTimelineTracks({
            tracks: [track],
            annotations: [],
            framePositionById: FRAME_POSITIONS
        });

        expect(withMaps).toMatchObject({ label: 'Vehicle', color: '#3366ff' });
        expect(withoutMaps).toMatchObject({ label: track.annotationClassId, color: undefined });
    });

    it('marks positions between keyframes as present only where an interpolated annotation exists', () => {
        const { track } = createWorkspaceFixture();
        const annotation = createAnnotationFixture();
        const interpolated: CuboidAnnotation = {
            ...annotation,
            id: 'annotation-1',
            frameId: 'frame-2',
            keyframeId: null
        };

        const [result] = toTimelineTracks({
            tracks: [track],
            annotations: [annotation, interpolated],
            framePositionById: FRAME_POSITIONS
        });

        // frame-1 has no annotation for this track: a gap between the two present positions.
        expect(result.presentFramePositions).toEqual([0, 2]);
    });

    it('drops annotations and keyframes referencing a frame the timeline has not discovered', () => {
        const { track } = createWorkspaceFixture();
        const annotation: CuboidAnnotation = { ...createAnnotationFixture(), frameId: 'frame-9' };

        const [result] = toTimelineTracks({
            tracks: [
                {
                    ...track,
                    keyframes: [{ id: 'kf', frameId: 'frame-9', annotationId: annotation.id }]
                }
            ],
            annotations: [annotation],
            framePositionById: FRAME_POSITIONS
        });

        expect(result.keyframes).toEqual([]);
        expect(result.presentFramePositions).toEqual([]);
    });

    it('ignores annotations belonging to a different track', () => {
        const { track } = createWorkspaceFixture();
        const otherTrack: CuboidAnnotation = { ...createAnnotationFixture(), trackId: 'track-1' };

        const [result] = toTimelineTracks({
            tracks: [track],
            annotations: [otherTrack],
            framePositionById: FRAME_POSITIONS
        });

        expect(result.presentFramePositions).toEqual([]);
    });
});
