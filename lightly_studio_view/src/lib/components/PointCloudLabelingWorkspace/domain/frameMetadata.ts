import type { CameraFrame, FrameSource, Timestamp } from './contracts';
import { freezeRotation, freezeVector } from './coordinates';

/** Validates an exact decimal nanosecond timestamp and its clock identity. */
export function validateTimestamp(timestamp: Timestamp) {
    if (!/^-?\d+$/.test(timestamp.nanoseconds) || !timestamp.clockId) {
        throw new Error('A timestamp needs integer nanoseconds and a clock ID.');
    }
}

/** Validates the stable recording, stream, and message identity for a frame. */
export function validateFrameSource(source: FrameSource) {
    if (!source.recordingId || !source.streamId || !source.messageId) {
        throw new Error('A frame source needs recording, stream, and message identities.');
    }
    if (source.publishedAt !== null) validateTimestamp(source.publishedAt);
}

/** Validates camera dimensions, source metadata, and calibration against a point-cloud frame. */
export function validateCamera(camera: CameraFrame, coordinateFrameId: string) {
    validateTimestamp(camera.timestamp);
    validateFrameSource(camera.source);
    if (![camera.width, camera.height].every((size) => Number.isSafeInteger(size) && size > 0)) {
        throw new Error('Camera dimensions must be positive integer pixel counts.');
    }
    const calibration = camera.calibration;
    if (calibration === null) return;
    if (calibration.pointCloudCoordinateFrameId !== coordinateFrameId) {
        throw new Error('Camera calibration targets a different point-cloud coordinate frame.');
    }
    freezeRotation(calibration.rotation);
    freezeVector(calibration.translation);
    const { fx, fy, cx, cy } = calibration.intrinsics;
    if (![fx, fy, cx, cy].every(Number.isFinite) || fx <= 0 || fy <= 0) {
        throw new Error('Camera intrinsics must be finite with positive focal lengths.');
    }
}
