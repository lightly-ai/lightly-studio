import type { AnnotationView, CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { ProjectionSettings } from '../projectionSettings';
import type { AnnotationClassColor } from '../projectionOverlay';
/** One camera tile's decoding, overlays, and enlarged-dialog inputs. */
export interface CameraProjectionFrameProps {
    /** Dataset the recording belongs to. */
    datasetId: string;
    /** Recording that owns the frame. */
    recordingId?: string;
    /** MCAP channel to render. */
    channelId: number;
    /** Keyframe to decode from, in nanoseconds, as a string to preserve full precision. */
    keyframeTimestampNs?: string;
    /** Frame to show, in nanoseconds, as a string to preserve full precision. */
    logTimeNs?: string;
    /** Tile-size JPEG of the frame, from the tick data. */
    blob?: Blob;
    /** Studio slot name shown as the caption, e.g. `front`. */
    label: string;
    /** Point positions, intensities, and optional colors to render. */
    batch?: PointBatch;
    /** Annotations projected onto the camera frame. */
    annotations?: readonly AnnotationView[];
    /** Annotation classes and colors used to render cuboids. */
    annotationClasses?: readonly AnnotationClassColor[];
    /** Calibration used to project 3D geometry onto the image. */
    projection?: CameraProjectionView;
    /** Visibility and appearance settings for camera overlays. */
    projectionSettings?: ProjectionSettings;
    /** Updates camera overlay settings. */
    onProjectionSettingsChange?: (settings: ProjectionSettings) => void;
    /** Starts or pauses playback from the camera view. */
    onPlaybackToggle?: () => void;
}
