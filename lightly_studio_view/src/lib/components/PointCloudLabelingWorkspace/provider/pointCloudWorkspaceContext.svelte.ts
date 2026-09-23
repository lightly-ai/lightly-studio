import { getContext, setContext } from 'svelte';
import { useMcapSequenceSummary } from '$lib/hooks';
import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';

/**
 * Shared data and playback state for the point-cloud labeling workspace.
 *
 * The provider wraps `useMcapSequenceSummary` so the summary is fetched once at the workspace root
 * and its channels/status flow to every pane without prop drilling. It also owns the transport
 * position (`currentTick`, `isPlaying`) that the timeline and camera strip key their per-tick data
 * off. Per-tile fetches (e.g. tick details in the camera strip) stay with their consumers.
 */
export type WorkspaceStatus = 'loading' | 'unsupported' | 'empty' | 'error' | 'ready';

export interface PointCloudWorkspaceContext {
    readonly datasetId: string;
    readonly sequenceId: string;
    /** Derived from the summary query; `unsupported` is only ever forced from outside. */
    readonly status: WorkspaceStatus;
    readonly lidarChannels: ChannelSummaryView[];
    readonly cameraChannels: ChannelSummaryView[];
    readonly ticks: TickView[];
    readonly currentTick: number;
    readonly isPlaying: boolean;
    goToPreviousFrame: () => void;
    goToNextFrame: () => void;
    togglePlayback: () => void;
    /** Re-fetch the sequence summary after a recoverable error. */
    retry: () => void;
}

const CONTEXT_KEY = 'point-cloud-workspace';

export const createPointCloudWorkspaceContext = (
    getInputs: () => {
        datasetId: string;
        sequenceId: string;
        /** Overrides the summary-derived status; for tests/stories. */
        statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
    }
): PointCloudWorkspaceContext => {
    const { summary, refetch } = useMcapSequenceSummary({
        getDatasetId: () => getInputs().datasetId,
        getSequenceId: () => getInputs().sequenceId
    });

    // Placeholder ruler until browser-side MCAP frame loading lands (child issues of LIG-10657).
    const ticks: TickView[] = Array.from({ length: 24 }, (_, index) => ({
        seq_number: index,
        timestamp_ns: null
    }));

    let currentTick = $state(0);
    let isPlaying = $state(false);

    const status = $derived.by((): WorkspaceStatus => {
        const override = getInputs().statusOverride;
        if (override) return override;
        // `isLoading` (not `isPending`) so the disabled query — no dataset/sequence yet — reads as
        // `empty` rather than a perpetual spinner.
        if (summary.isLoading) return 'loading';
        if (summary.isError) return 'error';
        if (!summary.data || summary.data.lidar_channels.length === 0) return 'empty';
        return 'ready';
    });

    const lidarChannels = $derived(summary.data?.lidar_channels ?? []);
    const cameraChannels = $derived(summary.data?.camera_channels ?? []);

    const context: PointCloudWorkspaceContext = {
        get datasetId() {
            return getInputs().datasetId;
        },
        get sequenceId() {
            return getInputs().sequenceId;
        },
        get status() {
            return status;
        },
        get lidarChannels() {
            return lidarChannels;
        },
        get cameraChannels() {
            return cameraChannels;
        },
        get ticks() {
            return ticks;
        },
        get currentTick() {
            return currentTick;
        },
        get isPlaying() {
            return isPlaying;
        },
        goToPreviousFrame() {
            if (currentTick > 0) currentTick -= 1;
        },
        goToNextFrame() {
            if (currentTick < ticks.length - 1) currentTick += 1;
        },
        togglePlayback() {
            isPlaying = !isPlaying;
        },
        retry: refetch
    };

    setContext(CONTEXT_KEY, context);
    return context;
};

export const usePointCloudWorkspaceContext = (): PointCloudWorkspaceContext => {
    const context = getContext<PointCloudWorkspaceContext>(CONTEXT_KEY);
    if (!context) {
        throw new Error('PointCloudWorkspaceContext not found');
    }
    return context;
};
