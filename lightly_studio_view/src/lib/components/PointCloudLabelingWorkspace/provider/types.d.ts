import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';
import type { useTickDetails } from '$lib/hooks/useTickDetails/useTickDetails';
import type { useCloudPointFrame } from '$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte';

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
    /** Details for the active tick, used to resolve channel payloads. */
    readonly tickDetails: ReturnType<typeof useTickDetails>['tickDetails'];
    /** Combined point cloud for all lidar channels in the active tick. */
    readonly cloudPointFrame: ReturnType<typeof useCloudPointFrame>['query'];
    readonly ticks: TickView[];
    /** Sequence ticks whose point-cloud frame is available from the query cache. */
    readonly cachedTicks: number[];
    readonly currentTick: number;
    readonly isPlaying: boolean;
    readonly playbackIntervalMs: number;
    goToFrame: (seqNumber: number) => void;
    goToPreviousFrame: () => void;
    goToNextFrame: () => void;
    togglePlayback: () => void;
    setPlaybackIntervalMs: (intervalMs: number) => void;
    /** Re-fetch the sequence summary, ticks, and active frame after a recoverable error. */
    retry: () => void;
}
