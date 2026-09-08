import { describe, expect, it } from 'vitest';
import {
    assertCompatibleCoordinates,
    canonicalCoordinateFrame,
    createCuboidAnnotation,
    createPointCloudFrame
} from './index';
import {
    createAnnotationFixture,
    createCameraFixture,
    createFrameFixtures,
    createWorkspaceFixture
} from './fixtures';

const SOURCE = {
    recordingId: 'rec-0',
    streamId: 'lidar-0',
    messageId: '0',
    publishedAt: null
} as const;

const TIMESTAMP = { nanoseconds: '1000000000', clockId: 'rec-0' } as const;

const FRAME = canonicalCoordinateFrame('lidar-0');

describe('point-cloud domain contracts', () => {
    it('computes null bounds for an empty frame and finite bounds for a populated frame', () => {
        const empty = createPointCloudFrame({
            id: 'f',
            source: SOURCE,
            timestamp: TIMESTAMP,
            sourcePointCount: 0,
            coordinateFrame: FRAME,
            positions: new Float32Array([]),
            cameras: []
        });
        expect(empty.bounds).toBeNull();

        const positions = new Float32Array([1, 0, 0, 3, 0, 1.5]);
        const populated = createPointCloudFrame({
            id: 'f',
            source: SOURCE,
            timestamp: TIMESTAMP,
            sourcePointCount: 2,
            coordinateFrame: FRAME,
            positions,
            cameras: []
        });
        expect(populated.bounds).toEqual({ min: [1, 0, 0], max: [3, 0, 1.5] });
    });

    it('omits optional attributes when not provided', () => {
        const frame = createPointCloudFrame({
            id: 'f',
            source: SOURCE,
            timestamp: TIMESTAMP,
            sourcePointCount: 1,
            coordinateFrame: FRAME,
            positions: new Float32Array([0, 0, 0]),
            cameras: []
        });
        expect(frame.intensity).toBeUndefined();
        expect(frame.color).toBeUndefined();
    });

    it('rejects malformed position buffers', () => {
        const base = {
            id: 'f',
            source: SOURCE,
            timestamp: TIMESTAMP,
            sourcePointCount: 1,
            coordinateFrame: FRAME,
            cameras: []
        };
        expect(() =>
            createPointCloudFrame({ ...base, positions: new Float32Array([1, 2]) })
        ).toThrow();
        expect(() =>
            createPointCloudFrame({ ...base, positions: new Float32Array([NaN, 0, 0]) })
        ).toThrow();
        expect(() =>
            createPointCloudFrame({
                ...base,
                positions: new Float32Array([0, 0, 0]),
                intensity: new Float32Array([])
            })
        ).toThrow();
        expect(() =>
            createPointCloudFrame({
                ...base,
                positions: new Float32Array([0, 0, 0]),
                color: new Float32Array([2, 0, 0])
            })
        ).toThrow();
    });

    it('isolates provider and renderer buffers and freezes shared metadata', () => {
        const positions = new Float32Array([0, 0, 0]);
        const frame = createPointCloudFrame({
            id: 'f',
            source: SOURCE,
            timestamp: TIMESTAMP,
            sourcePointCount: 1,
            coordinateFrame: FRAME,
            positions,
            cameras: []
        });
        positions[0] = 99;
        const rendererBuffer = frame.positions.copy();
        rendererBuffer.fill(42);
        expect(frame.positions.copy()[0]).toBe(0);
        expect(() => Object.assign(frame.timestamp, { nanoseconds: '0' })).toThrow();
    });

    it('round-trips canonical annotations through JSON without sharing mutable geometry', () => {
        const annotation = createCuboidAnnotation({
            id: 'a',
            frameId: 'f',
            coordinateFrame: FRAME,
            annotationClassId: 'car',
            annotationSourceId: 'gt',
            trackId: 'track-0',
            keyframeId: 'kf-0',
            center: [1, 0, 0],
            size: [2, 1, 1],
            rotation: [0, 0, 0, 1]
        });
        const decoded = JSON.parse(JSON.stringify(annotation));
        const restored = createCuboidAnnotation(decoded);
        decoded.center[0] = 100;
        expect(restored).toEqual(annotation);
        expect(() => Object.assign(restored.rotation, { 0: 1 })).toThrow();
        expect(() => createCuboidAnnotation({ ...annotation, size: [0, 1, 1] })).toThrow();
        expect(() => createCuboidAnnotation({ ...annotation, rotation: [0, 0, 0, 2] })).toThrow();
    });

    it('rejects implicit changes of origin, axes or units', () => {
        const frame = canonicalCoordinateFrame('lidar-0');
        expect(() => assertCompatibleCoordinates(frame, frame)).not.toThrow();
        for (const incompatible of [
            { ...frame, id: 'world' },
            { ...frame, unit: 'millimetre' },
            { ...frame, convention: 'y-up' }
        ]) {
            expect(() =>
                assertCompatibleCoordinates(JSON.parse(JSON.stringify(incompatible)), frame)
            ).toThrow();
        }
    });

    it('rejects sparse vectors and quaternions at the geometry boundary', () => {
        const annotation = createAnnotationFixture();
        const mutableCenter = Array<number>(3);
        mutableCenter[0] = 10;
        mutableCenter[2] = 1;
        const sparseCenter = mutableCenter as unknown as typeof annotation.center;
        const mutableRotation = Array<number>(4);
        mutableRotation[3] = 1;
        const sparseRotation = mutableRotation as unknown as typeof annotation.rotation;
        expect(() => createCuboidAnnotation({ ...annotation, center: sparseCenter })).toThrow();
        expect(() => createCuboidAnnotation({ ...annotation, rotation: sparseRotation })).toThrow();
    });

    it('rejects a keyframe annotation without a track', () => {
        const annotation = createAnnotationFixture();
        expect(() =>
            createCuboidAnnotation({ ...annotation, trackId: null, keyframeId: 'kf-0' })
        ).toThrow();
    });
});

describe('point-cloud fixtures', () => {
    it('createCameraFixture returns a calibrated camera with deterministic fields', () => {
        const camera = createCameraFixture();
        expect(camera.id).toBe('camera-0');
        expect(camera.calibration).not.toBeNull();
        expect(camera.image).not.toBeNull();
        expect(camera.width).toBe(640);
        expect(camera.height).toBe(480);
    });

    it('createFrameFixtures covers empty, normal, large, partial and malformed inputs', () => {
        const fixtures = createFrameFixtures();
        expect(fixtures.empty.bounds).toBeNull();
        expect(fixtures.normal.bounds).not.toBeNull();
        expect(fixtures.large.positions.length).toBeGreaterThan(1_000_000);
        expect(fixtures.partial.intensity).toBeUndefined();
        expect(fixtures.partial.cameras[0].image).toBeNull();
        fixtures.malformed.forEach((input) => expect(() => createPointCloudFrame(input)).toThrow());
    });

    it('createWorkspaceFixture has consistent track and annotation class identities', () => {
        const annotation = createAnnotationFixture();
        const workspace = createWorkspaceFixture();
        expect(workspace.track.id).toBe(annotation.trackId);
        expect(workspace.track.keyframes[0].annotationId).toBe(annotation.id);
        expect(workspace.annotationClass.id).toBe(annotation.annotationClassId);
        expect(workspace.interaction.selection.annotationIds).toContain(annotation.id);
    });
});
