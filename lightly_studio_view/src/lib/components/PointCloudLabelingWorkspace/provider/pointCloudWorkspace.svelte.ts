import {
    useCloudPointFrame,
    useMcapSequenceSummary,
    useMcapSequenceTicks,
    useTickDetails
} from '$lib/hooks';
import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointCloudWorkspaceContext, WorkspaceStatus } from './types';

export type GetInputs = () => {
    datasetId: string;
    sequenceId: string;
    /** 0-based seq number the transport starts on; defaults to the first tick. */
    initialTick?: number;
    /** Selected LiDAR channel IDs; undefined means all channels are shown. */
    selectedLidarChannels?: number[];
    /** Overrides the summary-derived status; for tests/stories. */
    statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
};

type SequenceSummary = ReturnType<typeof useMcapSequenceSummary>['summary'];
type SequenceTicks = ReturnType<typeof useMcapSequenceTicks>['ticks'];
type TickDetails = ReturnType<typeof useTickDetails>['tickDetails'];
type CloudPointQuery = ReturnType<typeof useCloudPointFrame>['query'];
type CloudPointFrameParams = ReturnType<Parameters<typeof useCloudPointFrame>[0]>;

function createTickDetails(getInputs: GetInputs, getCurrentTick: () => number): TickDetails {
    return useTickDetails({
        getDatasetId: () => getInputs().datasetId,
        getSequenceId: () => getInputs().sequenceId,
        getSeqNumber: getCurrentTick
    }).tickDetails;
}

function getChannelLocators(
    lidarChannels: ChannelSummaryView[],
    details: TickDetails['data'],
    selectedChannels?: number[]
) {
    if (!details) return [];
    return lidarChannels
        .filter(
            (channel) =>
                selectedChannels === undefined || selectedChannels.includes(channel.channel_id)
        )
        .flatMap((channel) => {
            const locator = details.channels[channel.group_component_name];
            return locator
                ? [{ channelId: locator.channel_id, timestampNs: locator.log_time_ns }]
                : [];
        });
}

function createCloudPointFrameParamsGetter(
    getInputs: GetInputs,
    tickDetails: TickDetails,
    summary: SequenceSummary
): () => CloudPointFrameParams {
    return () => ({
        datasetId: getInputs().datasetId,
        recordingId: tickDetails.data?.recording_id ?? '',
        channels: getChannelLocators(
            summary.data?.lidar_channels ?? [],
            tickDetails.data,
            getInputs().selectedLidarChannels
        )
    });
}

function createRetryHandler(
    refetchSummary: () => unknown,
    refetchTicks: () => unknown,
    tickDetails: TickDetails,
    cloudPointFrame: CloudPointQuery,
    getCloudPointFrameParams: () => CloudPointFrameParams
): () => void {
    return () => {
        void refetchSummary();
        void refetchTicks();
        void tickDetails.refetch();
        const { datasetId, recordingId, channels } = getCloudPointFrameParams();
        if (datasetId && recordingId && channels.length > 0) void cloudPointFrame.refetch();
    };
}

/**
 * Owns the shared data and playback state for the point-cloud labeling workspace.
 *
 * Fetches the sequence summary and ordered ticks once at the root so they flow to every pane
 * without prop drilling. Owns the transport position (`currentTick`, `isPlaying`) and loads the
 * active tick's point-cloud data. Instantiate via `createPointCloudWorkspaceContext`.
 */
export class PointCloudWorkspace implements PointCloudWorkspaceContext {
    currentTick = $state(0);
    isPlaying = $state(false);
    playbackIntervalMs = $state(300);

    readonly #getInputs: GetInputs;
    readonly #summary: ReturnType<typeof useMcapSequenceSummary>['summary'];
    readonly #sequenceTicks: SequenceTicks;
    readonly tickDetails: ReturnType<typeof useTickDetails>['tickDetails'];
    readonly cloudPointFrame: ReturnType<typeof useCloudPointFrame>['query'];
    readonly retry: () => void;

    // `$derived` is lazy, so referencing `this.#summary` here is safe — the body runs only when
    // the field is read, by which point the constructor has assigned it.
    readonly status = $derived.by((): WorkspaceStatus => {
        const override = this.#getInputs().statusOverride;
        if (override) return override;
        // `isLoading` (not `isPending`) so the disabled query — no dataset/sequence yet — reads as
        // `empty` rather than a perpetual spinner.
        if (this.#summary.isLoading) return 'loading';
        if (this.#summary.isError) return 'error';
        if (!this.#summary.data || this.#summary.data.lidar_channels.length === 0) return 'empty';
        if (this.#sequenceTicks.isLoading) return 'loading';
        if (this.#sequenceTicks.isError) return 'error';
        return 'ready';
    });

    readonly lidarChannels = $derived.by(() => this.#summary.data?.lidar_channels ?? []);
    readonly cameraChannels = $derived.by(() => this.#summary.data?.camera_channels ?? []);
    readonly ticks: TickView[] = $derived.by(() => this.#sequenceTicks.data?.ticks ?? []);

    constructor(getInputs: GetInputs) {
        const { summary, refetch } = useMcapSequenceSummary({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId
        });
        this.#getInputs = getInputs;
        this.#summary = summary;
        const { ticks, refetch: refetchTicks } = useMcapSequenceTicks({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId
        });
        this.#sequenceTicks = ticks;
        // Read once at construction: this is the starting position, not a reactive binding.
        this.currentTick = getInputs().initialTick ?? 0;
        const tickDetails = createTickDetails(getInputs, () => this.currentTick);
        const getCloudPointFrameParams = createCloudPointFrameParamsGetter(
            getInputs,
            tickDetails,
            summary
        );
        const cloudPointFrame = useCloudPointFrame(getCloudPointFrameParams).query;
        this.tickDetails = tickDetails;
        this.cloudPointFrame = cloudPointFrame;
        this.retry = createRetryHandler(
            refetch,
            refetchTicks,
            tickDetails,
            cloudPointFrame,
            getCloudPointFrameParams
        );
    }

    get datasetId(): string {
        return this.#getInputs().datasetId;
    }

    get sequenceId(): string {
        return this.#getInputs().sequenceId;
    }

    goToFrame = (seqNumber: number): void => {
        this.currentTick = seqNumber;
    };

    goToPreviousFrame = (): void => {
        const index = this.ticks.findIndex((tick) => tick.seq_number === this.currentTick);
        if (index > 0) this.currentTick = this.ticks[index - 1].seq_number;
        else if (index === -1) this.currentTick = this.ticks[0]?.seq_number ?? this.currentTick;
    };

    goToNextFrame = (): void => {
        const index = this.ticks.findIndex((tick) => tick.seq_number === this.currentTick);
        if (index === -1) this.currentTick = this.ticks[0]?.seq_number ?? this.currentTick;
        else if (index < this.ticks.length - 1) {
            this.currentTick = this.ticks[index + 1].seq_number;
        }
    };

    togglePlayback = (): void => {
        if (
            !this.isPlaying &&
            this.ticks.length > 0 &&
            this.currentTick === this.ticks.at(-1)?.seq_number
        ) {
            this.currentTick = this.ticks[0].seq_number;
        }
        this.isPlaying = !this.isPlaying;
    };

    setPlaybackIntervalMs = (intervalMs: number): void => {
        this.playbackIntervalMs = intervalMs;
    };
        this.isPlaying = !this.isPlaying;
    };
}
