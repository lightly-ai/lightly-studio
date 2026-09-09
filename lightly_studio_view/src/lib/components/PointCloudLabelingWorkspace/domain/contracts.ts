/** A canonical position or translation: x forward, y left, z up, in meters. */
export type Vector3 = readonly [number, number, number];
/** An active local-to-parent rotation in unit quaternion order x, y, z, w. */
export type Quaternion = readonly [number, number, number, number];

/** Identifies the origin, axes, handedness, and unit used by geometry. */
export interface CoordinateFrame {
    /** Stable identifier for the physical or recording frame. */
    readonly id: string;
    /** The only convention accepted by the canonical domain model. */
    readonly convention: 'right-handed-x-forward-y-left-z-up';
    /** The canonical distance unit. */
    readonly unit: 'meter';
}

/** Rectified pinhole intrinsics measured in image pixels. */
export interface CameraIntrinsics {
    /** Horizontal focal length in pixels. */
    readonly fx: number;
    /** Vertical focal length in pixels. */
    readonly fy: number;
    /** Principal-point horizontal coordinate in pixels. */
    readonly cx: number;
    /** Principal-point vertical coordinate in pixels. */
    readonly cy: number;
}

/** A nanosecond timestamp that remains exact across browser and worker boundaries. */
export interface Timestamp {
    /** Integer nanoseconds as a decimal string; never convert epoch nanoseconds to Number. */
    readonly nanoseconds: string;
    /** Only timestamps with the same clock ID can be compared. */
    readonly clockId: string;
}

export interface FrameSource {
    /** Recording or MCAP file identity. */
    readonly recordingId: string;
    /** Stable stream identity (for example, an MCAP channel), not a display name. */
    readonly streamId: string;
    /** Stable message identity within the stream; timestamps alone are not unique. */
    readonly messageId: string;
    /** Source publication time, independent of the recording timeline timestamp. */
    readonly publishedAt: Timestamp | null;
}

export interface Bounds3 {
    /** Inclusive minimum x, y, and z values. */
    readonly min: Vector3;
    /** Inclusive maximum x, y, and z values. */
    readonly max: Vector3;
}

/** Owned packed data. Each export is a copy, suitable for transfer to a renderer. */
export interface PackedPointAttribute {
    /** Number of scalar values in the packed buffer. */
    readonly length: number;
    /** Returns a new buffer that can be uploaded or transferred by the caller. */
    readonly copy: () => Float32Array;
}

/** Immutable point-cloud data consumed by providers, workers, and renderers. */
export interface PointCloudFrame {
    /** Stable across reloads and point-budget changes; scoped to recording/stream/message. */
    readonly id: string;
    readonly source: FrameSource;
    /** Recording timeline time (MCAP logTime), not publication or sensor acquisition time. */
    readonly timestamp: Timestamp;
    /** Count before filtering/downsampling; displayed count is positions.length / 3. */
    readonly sourcePointCount: number;
    /** The coordinate system shared by positions, bounds, and cameras. */
    readonly coordinateFrame: CoordinateFrame;
    /** Packed xyz triples, no stride or padding. All coordinates must be finite. */
    readonly positions: PackedPointAttribute;
    /** One normalized [0, 1] value per point, when available. */
    readonly intensity?: PackedPointAttribute;
    /** Packed linear RGB triples in [0, 1], when available. */
    readonly color?: PackedPointAttribute;
    /** Null exactly when the frame has no points. */
    readonly bounds: Bounds3 | null;
    /** Camera context associated with this recording time. */
    readonly cameras: readonly CameraFrame[];
}

/** Pinhole calibration that maps camera coordinates into a point-cloud frame. */
export interface CameraCalibration {
    /** Stable calibration record identity. */
    readonly id: string;
    /** Coordinate frame receiving transformed camera points. */
    readonly pointCloudCoordinateFrameId: string;
    /** Camera optical axes: x right, y down, z forward, in meters. */
    readonly cameraCoordinateFrameId: string;
    /** Camera-to-point-cloud transform: p_cloud = R(q) * p_camera + translation. */
    /** Camera-to-point-cloud translation in meters. */
    readonly translation: Vector3;
    /** Camera-to-point-cloud active rotation. */
    readonly rotation: Quaternion;
    /** Rectified pinhole intrinsics in pixels; origin at top-left pixel centre. */
    readonly intrinsics: CameraIntrinsics;
}

/** An image URI or an adapter-owned decoded resource reference. */
export type CameraImage =
    | Readonly<{ kind: 'uri'; uri: string }>
    | Readonly<{ kind: 'decoded'; resourceId: string }>;

/** A camera image and optional calibration available near a point-cloud frame. */
export interface CameraFrame {
    /** Stable camera stream identity. */
    readonly id: string;
    readonly source: FrameSource;
    readonly timestamp: Timestamp;
    /** Image dimensions in pixels. */
    readonly width: number;
    readonly height: number;
    /** Decoded resources (e.g. ImageBitmap) are owned/disposed by the camera adapter. */
    readonly image: CameraImage | null;
    /** Null means projection is unavailable; uncalibrated imagery can still be displayed. */
    readonly calibration: CameraCalibration | null;
}

/** JSON-compatible shape shared by persistence and rendering adapters. */
export interface CuboidAnnotation {
    /** Stable annotation identity across rendering and persistence. */
    readonly id: string;
    /** Point-cloud frame in which the geometry is expressed. */
    readonly frameId: string;
    /** Coordinate system shared with the referenced point-cloud frame. */
    readonly coordinateFrame: CoordinateFrame;
    /** Assigned annotation class identity. */
    readonly annotationClassId: string;
    /** Annotation source identity, such as ground truth or predictions. */
    readonly annotationSourceId: string;
    /** Track identity, or null for a single-frame annotation. */
    readonly trackId: string | null;
    /** Authored keyframe identity, or null for an untracked/interpolated annotation. */
    readonly keyframeId: string | null;
    /** Cuboid centre in the canonical coordinate frame. */
    readonly center: Vector3;
    /** Positive full extents along the cuboid's local x, y, z axes, in meters. */
    readonly size: Vector3;
    /** Cuboid orientation as a unit xyzw quaternion. */
    readonly rotation: Quaternion;
}

/** Display metadata for an annotation class. */
export interface AnnotationClass {
    /** Stable class identity used by annotations. */
    readonly id: string;
    /** Human-readable class name. */
    readonly name: string;
    /** CSS color used by renderers and panels. */
    readonly color: string;
}

/** Object identity and keyframe anchors across a frame sequence. */
/** An authored annotation anchor in a track. */
export interface AnnotationKeyframe {
    /** Stable keyframe identity. */
    readonly id: string;
    /** Frame containing the authored annotation. */
    readonly frameId: string;
    /** Annotation identity containing the authored geometry. */
    readonly annotationId: string;
}

export interface AnnotationTrack {
    /** Stable track identity. */
    readonly id: string;
    /** Class assigned to every annotation in this track. */
    readonly annotationClassId: string;
    /** Ordered authored keyframes for the track. */
    readonly keyframes: readonly AnnotationKeyframe[];
}

/** Tools available to the interaction state machine. */
export type WorkspaceTool =
    | 'select'
    | 'create-cuboid'
    | 'translate'
    | 'rotate'
    | 'resize'
    | 'pan'
    | 'orbit';
/** Main scene and orthographic camera modes. */
export type CameraMode = 'perspective' | 'top' | 'side' | 'front';
/** Handles that can be hovered or manipulated on a cuboid. */
export type CuboidHandle =
    | 'center'
    | 'rotate-z'
    | 'min-x'
    | 'max-x'
    | 'min-y'
    | 'max-y'
    | 'min-z'
    | 'max-z';

export interface AnnotationSelection {
    /** Ordered IDs; the last ID is the primary annotation for inspector and transforms. */
    readonly annotationIds: readonly string[];
}

export interface AnnotationHover {
    /** Annotation under the pointer. */
    readonly annotationId: string;
    /** Manipulation handle under the pointer, if any. */
    readonly handle: CuboidHandle | null;
}

/** Revisioned sets of pending persistence changes. */
export interface DirtyAnnotations {
    /** Monotonically increasing edit revision captured by save requests. */
    readonly revision: number;
    /** Annotation IDs whose latest values should be upserted. */
    readonly upsertAnnotationIds: readonly string[];
    /** Annotation IDs that should be removed. */
    readonly deletedAnnotationIds: readonly string[];
}

/** Framework-independent state shared by scene, panels, and timeline controls. */
export interface WorkspaceInteraction {
    /** Currently active editing or navigation tool. */
    readonly tool: WorkspaceTool;
    /** Frame displayed by the workspace, or null before a frame is selected. */
    readonly activeFrameId: string | null;
    /** Current 3D or orthographic camera mode. */
    readonly cameraMode: CameraMode;
    /** Ordered selected annotation identities. */
    readonly selection: AnnotationSelection;
    /** Current pointer target, if the pointer is over an annotation. */
    readonly hover: AnnotationHover | null;
    /** Upserts and deletions are disjoint; a successful save clears only its captured revision. */
    readonly dirty: DirtyAnnotations;
}
