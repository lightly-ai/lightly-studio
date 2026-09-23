import { getContext, setContext } from 'svelte';
import { useMcapSequenceSummary } from '$lib/hooks';
import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';

/**
 * Shared data and playback state for the point-cloud labeling workspace.
 *
 * Wraps `useMcapSequenceSummary` so the summary is fetched once at the root and flows to every pane
 * without prop drilling. Owns the transport position (`currentTick`, `isPlaying`); per-tile fetches
 * stay with their consumers.
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

type GetInputs = () => {
    datasetId: string;
    sequenceId: string;
    /** Overrides the summary-derived status; for tests/stories. */
    statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
};

class PointCloudWorkspace implements PointCloudWorkspaceContext {
    // Placeholder ruler until browser-side MCAP frame loading lands (child issues of LIG-10657).
    readonly ticks: TickView[] = Array.from({ length: 24 }, (_, index) => ({
        seq_number: index,
        timestamp_ns: null
    }));

    currentTick = $state(0);
    isPlaying = $state(false);

    readonly #getInputs: GetInputs;
    readonly #summary: ReturnType<typeof useMcapSequenceSummary>['summary'];
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
        return 'ready';
    });

    readonly lidarChannels = $derived.by(() => this.#summary.data?.lidar_channels ?? []);
    readonly cameraChannels = $derived.by(() => this.#summary.data?.camera_channels ?? []);

    constructor(getInputs: GetInputs) {
        const { summary, refetch } = useMcapSequenceSummary({
            getDatasetId: () => getInputs().datasetId,
            getSequenceId: () => getInputs().sequenceId
        });
        this.#getInputs = getInputs;
        this.#summary = summary;
        this.retry = refetch;
    }

    get datasetId(): string {
        return this.#getInputs().datasetId;
    }

    get sequenceId(): string {
        return this.#getInputs().sequenceId;
    }

    goToPreviousFrame(): void {
        if (this.currentTick > 0) this.currentTick -= 1;
    }

    goToNextFrame(): void {
        if (this.currentTick < this.ticks.length - 1) this.currentTick += 1;
    }

    togglePlayback(): void {
        this.isPlaying = !this.isPlaying;
    }
}

export const createPointCloudWorkspaceContext = (
    getInputs: GetInputs
): PointCloudWorkspaceContext => {
    const context = new PointCloudWorkspace(getInputs);
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
