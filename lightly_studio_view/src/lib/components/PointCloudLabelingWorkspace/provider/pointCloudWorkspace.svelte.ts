import { useMcapSequenceSummary, useSequenceTicks, useTickDetails } from '$lib/hooks';
import { useCloudPointFrame } from '$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import {
    toAnnotationClasses,
    toCuboidAnnotations
} from '$lib/components/PointCloudLabelingWorkspace/tickAnnotations/tickAnnotations';
import {
    accumulatePointCloud,
    type PointCloudAccumulation
} from '$lib/components/PointCloudLabelingWorkspace/pointCloudAccumulation/pointCloudAccumulation';
import type { PointCloudWorkspaceContext, WorkspaceStatus } from './types';

export type GetInputs = () => {
    datasetId: string;
    sequenceId: string;
    /** 0-based seq number the transport starts on; defaults to the first tick. */
    initialTick?: number;
    /** Overrides the summary-derived status; for tests/stories. */
    statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
};

/**
 * Owns the shared data and playback state for the point-cloud labeling workspace.
 *
 * Wraps `useMcapSequenceSummary` so the summary is fetched once at the root and flows to every pane
 * without prop drilling. Owns the transport position (`currentTick`, `isPlaying`) and loads the
 * active tick's point-cloud data. Instantiate via `createPointCloudWorkspaceContext`.
 */
export class PointCloudWorkspace implements PointCloudWorkspaceContext {
    currentTick = $state(0);
    isPlaying = $state(false);
    // The first frame is the default. A pick is kept only while it is still in the list, and
    // it is keyed by its source so it resets when the dataset or the sequence changes.
    #pickedReferenceFrame = $state<{ source: string; frameId: string } | null>(null);

    readonly #getInputs: GetInputs;
    readonly #summary: ReturnType<typeof useMcapSequenceSummary>['summary'];
    readonly #sequenceTicks: ReturnType<typeof useSequenceTicks>['sequenceTicks'];
    readonly tickDetails: ReturnType<typeof useTickDetails>['tickDetails'];
    readonly cloudPointFrame: ReturnType<typeof useCloudPointFrame>['query'];
    readonly retry: () => void;
    #playbackFrame: number | undefined;

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
        return 'ready';
    });

    readonly ticks = $derived.by(() => this.#sequenceTicks.data?.ticks ?? []);

    readonly lidarChannels = $derived.by(() => this.#summary.data?.lidar_channels ?? []);

    readonly referenceFrames = $derived.by(() => this.#summary.data?.reference_frames ?? []);
    readonly referenceFrameId = $derived.by(() => {
        const frames = this.referenceFrames;
        const picked = this.#pickedReferenceFrame;
        if (
            picked?.source === this.#source &&
            frames.some((frame) => frame.id === picked.frameId)
        ) {
            return picked.frameId;
        }
        return frames[0]?.id ?? '';
    });

    // `null` until the user picks channels, so every lidar channel is shown by default. The pick
    // is keyed by its source, so it resets when the dataset or the sequence changes.
    #pickedLidarChannels = $state<{ source: string; channelIds: number[] } | null>(null);
    readonly selectedLidarChannels = $derived.by(() =>
        this.#pickedLidarChannels?.source === this.#source
            ? this.#pickedLidarChannels.channelIds
            : this.lidarChannels.map((channel) => channel.channel_id)
    );
    readonly cameraChannels = $derived.by(() => this.#summary.data?.camera_channels ?? []);

    readonly cuboids = $derived.by(() =>
        toCuboidAnnotations(this.tickDetails.data?.annotations ?? [])
    );
    readonly annotationClasses = $derived.by(() => toAnnotationClasses(this.cuboids));

    accumulatePointClouds = $state(false);
    // Points shown so far while accumulating. Not reactive: `displayedBatch` updates it as a
    // cache, and it is keyed so it resets when the source, frame, or channel pick changes.
    #accumulation: PointCloudAccumulation | null = null;

    readonly displayedBatch = $derived.by((): PointBatch | undefined => {
        const frame = this.cloudPointFrame.data;
        if (!frame || !this.accumulatePointClouds) {
            this.#accumulation = null;
            return frame?.batch;
        }
        // Placeholder data is the previous load, which can belong to another frame or pick.
        if (this.cloudPointFrame.isPlaceholderData && this.#accumulation) {
            return this.#accumulation.batch;
        }
        const key = `${this.#source}/${this.referenceFrameId}/${this.selectedLidarChannels.join(',')}`;
        this.#accumulation = accumulatePointCloud(this.#accumulation, key, frame);
        return this.#accumulation.batch;
    });

    constructor(getInputs: GetInputs) {
        const { summary, refetch } = useMcapSequenceSummary({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId
        });
        this.#getInputs = getInputs;
        this.#summary = summary;
        const { sequenceTicks } = useSequenceTicks({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId
        });
        this.#sequenceTicks = sequenceTicks;
        // Read once at construction: this is the starting position, not a reactive binding.
        this.currentTick = getInputs().initialTick ?? 0;
        const { tickDetails } = useTickDetails({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId,
            getSeqNumber: () => this.currentTick,
            // The cuboids are mapped into the frame of the point clouds, so that the two align.
            getTargetFrameId: () => this.referenceFrameId
        });
        const channels = $derived.by(() => {
            const details = tickDetails.data;
            if (!details) return [];
            return this.lidarChannels.flatMap((channel) => {
                if (!this.selectedLidarChannels.includes(channel.channel_id)) return [];
                const locator = details.channels[channel.group_component_name];
                return locator
                    ? [{ channelId: locator.channel_id, timestampNs: String(locator.log_time_ns) }]
                    : [];
            });
        });
        const { query } = useCloudPointFrame(() => ({
            datasetId: getInputs().datasetId,
            recordingId: tickDetails.data?.recording_id ?? '',
            channels,
            targetFrameId: this.referenceFrameId
        }));
        this.tickDetails = tickDetails;
        this.cloudPointFrame = query;
        this.retry = () => {
            void refetch();
            void sequenceTicks.refetch();
            void tickDetails.refetch();
            void query.refetch();
        };
    }

    get datasetId(): string {
        return this.#getInputs().datasetId;
    }

    get sequenceId(): string {
        return this.#getInputs().sequenceId;
    }

    // Arrow function, because the filter bar passes it as an event handler without the instance.
    selectReferenceFrame = (frameId: string): void => {
        if (this.referenceFrames.some((frame) => frame.id === frameId)) {
            this.#pickedReferenceFrame = { source: this.#source, frameId };
        }
    };

    toggleLidarChannel(channelId: number): void {
        const selected = this.selectedLidarChannels;
        this.#pickedLidarChannels = {
            source: this.#source,
            channelIds: selected.includes(channelId)
                ? selected.filter((id) => id !== channelId)
                : [...selected, channelId]
        };
    }

    // Arrow function, because the filter bar passes it as an event handler without the instance.
    setAccumulatePointClouds = (accumulate: boolean): void => {
        this.accumulatePointClouds = accumulate;
    };

    get #source(): string {
        return `${this.datasetId}/${this.sequenceId}`;
    }

    // Arrow functions, because the panes pass these as event handlers without the instance.
    goToPreviousFrame = (): void => {
        this.#stepFrame(-1);
    };

    goToNextFrame = (): void => {
        this.#stepFrame(1);
    };

    togglePlayback = (): void => {
        if (this.isPlaying) {
            this.#stopPlayback();
            return;
        }
        // Play from the start again once the end of the sequence is reached.
        if (this.ticks.at(-1)?.seq_number === this.currentTick) {
            this.currentTick = this.ticks[0].seq_number;
        }
        this.isPlaying = true;
        this.#playbackFrame = requestAnimationFrame(this.#advancePlayback);
    };

    /** Stops playback; call when the workspace unmounts. */
    dispose(): void {
        this.#stopPlayback();
    }

    // Playback runs as fast as the frames load: it checks once per animation frame and steps as
    // soon as the current frame is on screen, not while the previous frame is still shown.
    #advancePlayback = (): void => {
        const isLoading =
            this.tickDetails.isFetching ||
            this.cloudPointFrame.isFetching ||
            this.cloudPointFrame.isPlaceholderData;
        if (!isLoading) {
            const index = this.ticks.findIndex((tick) => tick.seq_number === this.currentTick);
            if (index < 0 || index >= this.ticks.length - 1) {
                this.#stopPlayback();
                return;
            }
            this.#stepFrame(1);
        }
        this.#playbackFrame = requestAnimationFrame(this.#advancePlayback);
    };

    #stopPlayback(): void {
        if (this.#playbackFrame !== undefined) cancelAnimationFrame(this.#playbackFrame);
        this.#playbackFrame = undefined;
        this.isPlaying = false;
    }

    // Ticks can be sparse, so step by position in the list rather than by seq number.
    #stepFrame(offset: number): void {
        const index = this.ticks.findIndex((tick) => tick.seq_number === this.currentTick);
        const next = index < 0 ? undefined : this.ticks[index + offset];
        if (next) this.currentTick = next.seq_number;
    }
}
