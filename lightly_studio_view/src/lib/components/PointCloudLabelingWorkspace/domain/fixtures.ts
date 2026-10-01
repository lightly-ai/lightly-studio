import { canonicalCoordinateFrame, createCuboidAnnotation } from './coordinates';
import { createPointCloudFrame } from './pointCloudFrame';
import type {
    AnnotationClass,
    AnnotationTrack,
    CameraFrame,
    PointCloudFrame,
    WorkspaceInteraction
} from './contracts';

type FrameFixtureInput = Parameters<typeof createPointCloudFrame>[0];

/** Named fixture set used by provider, renderer, and workspace contract tests. */
export interface PointCloudFrameFixtures {
    readonly empty: PointCloudFrame;
    readonly normal: PointCloudFrame;
    readonly large: PointCloudFrame;
    readonly partial: PointCloudFrame;
    readonly malformed: readonly FrameFixtureInput[];
}

/** Named fixture state shared by workspace and persistence tests. */
export interface WorkspaceFixture {
    readonly annotationClass: AnnotationClass;
    readonly track: AnnotationTrack;
    readonly interaction: WorkspaceInteraction;
}

/** Creates a calibrated camera fixture with deterministic source metadata. */
export function createCameraFixture(): CameraFrame {
    return {
        id: 'camera-0',
        source: {
            recordingId: 'recording-0',
            streamId: 'camera-stream-0',
            messageId: '0',
            publishedAt: null
        },
        timestamp: { nanoseconds: '1788220800123456789', clockId: 'recording-0' },
        width: 640,
        height: 480,
        image: {
            kind: 'uri',
            uri: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="640" height="480"/%3E'
        },
        calibration: {
            id: 'calibration-0',
            pointCloudCoordinateFrameId: 'lidar-0',
            cameraCoordinateFrameId: 'camera-optical-0',
            translation: [0, 0, 0],
            // Optical right/down/forward maps to canonical -y/-z/+x.
            rotation: [0.5, -0.5, 0.5, -0.5],
            intrinsics: { fx: 500, fy: 500, cx: 319.5, cy: 239.5 }
        }
    };
}

/** Fresh, deterministic inputs, including an epoch beyond Number's integer precision. */
export function createFrameInput(pointCount = 4): Parameters<typeof createPointCloudFrame>[0] {
    const positions = new Float32Array(pointCount * 3);
    for (let i = 0; i < pointCount; i++) {
        positions.set([i % 100, Math.floor(i / 100) % 100, (i % 7) / 2], i * 3);
    }
    return {
        id: 'frame-0',
        source: {
            recordingId: 'recording-0',
            streamId: 'lidar-stream-0',
            messageId: '0',
            publishedAt: { nanoseconds: '1788220800123000000', clockId: 'sensor-0' }
        },
        sourcePointCount: pointCount,
        timestamp: { nanoseconds: '1788220800123456789', clockId: 'recording-0' },
        coordinateFrame: canonicalCoordinateFrame('lidar-0'),
        positions,
        intensity: new Float32Array(pointCount).fill(0.5),
        color: new Float32Array(pointCount * 3).fill(0.25),
        cameras: [createCameraFixture()]
    };
}

/** Creates empty, normal, large, partial, and malformed frame fixtures. */
export function createFrameFixtures(): PointCloudFrameFixtures {
    const normal = createFrameInput();
    return {
        empty: createPointCloudFrame(createFrameInput(0)),
        normal: createPointCloudFrame(normal),
        large: createPointCloudFrame(createFrameInput(350_000)),
        partial: createPointCloudFrame({
            ...normal,
            intensity: undefined,
            color: undefined,
            cameras: [
                {
                    id: 'camera-0',
                    source: createCameraFixture().source,
                    timestamp: normal.timestamp,
                    width: 640,
                    height: 480,
                    image: null,
                    calibration: null
                }
            ]
        }),
        malformed: [
            { ...normal, positions: new Float32Array([1, 2]) },
            { ...normal, positions: new Float32Array([NaN, 0, 0]) },
            { ...normal, intensity: new Float32Array(1) },
            { ...normal, color: new Float32Array(12).fill(255) }
        ]
    };
}

/** Creates a canonical tracked cuboid annotation fixture. */
export function createAnnotationFixture() {
    return createCuboidAnnotation({
        id: 'annotation-0',
        frameId: 'frame-0',
        coordinateFrame: canonicalCoordinateFrame('lidar-0'),
        annotationClassId: 'vehicle',
        annotationSourceId: 'ground-truth',
        trackId: 'track-0',
        keyframeId: 'keyframe-0',
        center: [10, -2, 1],
        size: [4, 2, 2],
        rotation: [0, 0, 0, 1]
    });
}

/** Creates matching class, track, selection, and dirty-state fixtures. */
export function createWorkspaceFixture(): WorkspaceFixture {
    return {
        annotationClass: { id: 'vehicle', name: 'Vehicle', color: '#3366ff' },
        track: {
            id: 'track-0',
            annotationClassId: 'vehicle',
            keyframes: [{ id: 'keyframe-0', frameId: 'frame-0', annotationId: 'annotation-0' }]
        },
        interaction: {
            tool: 'select',
            activeFrameId: 'frame-0',
            cameraMode: 'perspective',
            selection: { annotationIds: ['annotation-0'] },
            hover: null,
            dirty: { revision: 1, upsertAnnotationIds: ['annotation-0'], deletedAnnotationIds: [] }
        }
    };
}
