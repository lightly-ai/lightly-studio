import { describe, expect, it } from 'vitest';
import {
    assertCompatibleCoordinates,
    canonicalCoordinateFrame,
    createCuboidAnnotation,
    createPointCloudFrame
} from './index';
import {
    createAnnotationFixture,
    createFrameFixtures,
    createFrameInput,
    createWorkspaceFixture
} from './fixtures';

describe('point-cloud domain contracts', () => {
    it('covers empty, populated, large, partial and malformed frames', () => {
        const fixtures = createFrameFixtures();
        expect(fixtures.empty.bounds).toBeNull();
        expect(fixtures.normal.bounds).toEqual({ min: [0, 0, 0], max: [3, 0, 1.5] });
        expect(fixtures.large.positions.length).toBe(1_050_000);
        expect(fixtures.partial.intensity).toBeUndefined();
        expect(fixtures.partial.cameras[0].image).toBeNull();
        fixtures.malformed.forEach((input) => expect(() => createPointCloudFrame(input)).toThrow());
    });

    it('isolates provider and renderer buffers and freezes shared metadata', () => {
        const input = createFrameInput();
        const frame = createPointCloudFrame(input);
        input.positions[0] = 99;
        const rendererBuffer = frame.positions.copy();
        rendererBuffer.fill(42);
        expect(frame.positions.copy()[0]).toBe(0);
        expect(frame.timestamp.nanoseconds).toBe('1788220800123456789');
        expect(() => Object.assign(frame.timestamp, { nanoseconds: '0' })).toThrow();
        expect(() => Object.assign(frame.bounds!.min, { 0: 42 })).toThrow();
        expect(() => Object.assign(frame.cameras[0].calibration!.intrinsics, { fx: 0 })).toThrow();
    });

    it('provides deterministic buffers and consistent track and selection identities', () => {
        expect(createFrameInput().positions).toEqual(createFrameInput().positions);
        const annotation = createAnnotationFixture();
        const workspace = createWorkspaceFixture();
        expect(workspace.track.id).toBe(annotation.trackId);
        expect(workspace.track.keyframes[0]).toEqual({
            id: annotation.keyframeId,
            frameId: annotation.frameId,
            annotationId: annotation.id
        });
        expect(workspace.annotationClass.id).toBe(annotation.annotationClassId);
        expect(workspace.interaction.selection.annotationIds).toContain(annotation.id);
    });

    it('round-trips canonical annotations through JSON without sharing mutable geometry', () => {
        const annotation = createAnnotationFixture();
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
            // Simulate untrusted provider metadata crossing the typed boundary.
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
});
