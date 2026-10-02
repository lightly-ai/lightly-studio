import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';
import type { useTickDetails } from '$lib/hooks/useTickDetails/useTickDetails';
import type { useCloudPointFrame } from '$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type {
    AnnotationClass,
    CuboidAnnotation
} from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Lifecycle of the workspace as a whole; drives which shell state is rendered. */
export type WorkspaceStatus = 'loading' | 'unsupported' | 'empty' | 'error' | 'ready';

/**
 * Shared data and playback state for the point-cloud labeling workspace.
 *
 * Fetched once at the root and flows to every pane without prop drilling. Owns the transport
 * position (`currentTick`, `isPlaying`); per-tile fetches stay with their consumers.
 */
export interface PointCloudWorkspaceContext {
    readonly datasetId: string;
    readonly sequenceId: string;
    /** Derived from the summary query; `unsupported` is only ever forced from outside. */
    readonly status: WorkspaceStatus;
    readonly lidarChannels: ChannelSummaryView[];
    readonly cameraChannels: ChannelSummaryView[];
    /** `channel_id`s of the lidar channels rendered in the scene; all of them by default. */
    readonly selectedLidarChannels: number[];
    /** Details for the active tick, used to resolve channel payloads. */
    readonly tickDetails: ReturnType<typeof useTickDetails>['tickDetails'];
    /** Combined point cloud for the selected lidar channels in the active tick. */
    readonly cloudPointFrame: ReturnType<typeof useCloudPointFrame>['query'];
    /** Whether new point clouds are added to the scene instead of replacing the shown ones. */
    readonly accumulatePointClouds: boolean;
    /** Turns accumulation on or off; turning it off shows only the active tick again. */
    setAccumulatePointClouds: (accumulate: boolean) => void;
    /** Points to render: the active tick, or every tick loaded so far while accumulating. */
    readonly displayedBatch: PointBatch | undefined;
    /** Frames the point clouds and the cuboids can be shown in. */
    readonly referenceFrames: readonly { readonly id: string; readonly name: string }[];
    /** Frame the point clouds and the cuboids are shown in; one of `referenceFrames`. */
    readonly referenceFrameId: string;
    /** Shows the scene in another of `referenceFrames`; ignores an unknown frame. */
    selectReferenceFrame: (frameId: string) => void;
    /** 3D cuboid annotations of the active tick. */
    readonly cuboids: CuboidAnnotation[];
    /** One class per label name used by `cuboids`, with its display color. */
    readonly annotationClasses: AnnotationClass[];
    readonly ticks: TickView[];
    readonly currentTick: number;
    readonly isPlaying: boolean;
    goToPreviousFrame: () => void;
    goToNextFrame: () => void;
    togglePlayback: () => void;
    /** Shows or hides a lidar channel in the scene by its `channel_id`. */
    toggleLidarChannel: (channelId: number) => void;
    /** Re-fetch the sequence summary after a recoverable error. */
    retry: () => void;
}
