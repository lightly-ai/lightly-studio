import type { ChannelSummaryView, AnnotationView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { AnnotationClassColor } from './projectionOverlay';
/** Data and actions needed to render the camera strip for one tick. */
export interface CameraProjectionStripProps {
    /** Dataset the sequence belongs to. */
    datasetId: string;
    /** MCAP sequence being labeled. */
    sequenceId: string;
    /** Zero-based tick position to render frames for. */
    seqNumber: number;
    /** Frame the workspace requests cuboids in, so both share one tick-details query. */
    displayFrameId?: string;
    /** All camera slots configured for the sequence; this is the stable tile layout. */
    cameraChannels: ChannelSummaryView[];
    /** Camera channel IDs currently shown in the projection strip. */
    selectedChannelIds: number[];
    /** Point positions, intensities, and optional colors to render. */
    batch?: PointBatch;
    /** Annotations projected onto the camera frame. */
    annotations?: readonly AnnotationView[];
    /** Annotation classes and colors used to render cuboids. */
    annotationClasses?: readonly AnnotationClassColor[];
    /** Whether geometry shares a usable projection coordinate frame. */
    canProject?: boolean;
    /** Starts or pauses playback from the camera view. */
    onPlaybackToggle?: () => void;
    /** Whether only the camera strip header is visible. */
    collapsed?: boolean;
    /** Expands or collapses the camera pane. */
    onToggleCollapsed?: () => void;
}
