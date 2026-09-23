import { useMcapSequenceSummary } from '$lib/hooks';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
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
 * without prop drilling. Owns the transport position (`currentTick`, `isPlaying`); per-tile fetches
 * stay with their consumers. Instantiate via `createPointCloudWorkspaceContext`.
 */
export class PointCloudWorkspace implements PointCloudWorkspaceContext {
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
        // Read once at construction: this is the starting position, not a reactive binding.
        this.currentTick = getInputs().initialTick ?? 0;
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
