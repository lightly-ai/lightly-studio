import type { Embeddings2dStatus } from '$lib/api/lightly_studio_local';

// A first PaCMAP compute above this many embeddings can run for minutes, so the panel asks first.
const PLOT_COMPUTE_CONFIRM_THRESHOLD = 250_000;

export type PlotComputeView = 'checking' | 'error' | 'prompt' | 'computing' | 'plot';

interface PlotComputeViewInput {
    status: Embeddings2dStatus | undefined;
    isStatusError: boolean;
    isAxesLayout: boolean;
    isComputeStarted: boolean;
}

export function getPlotComputeView(input: PlotComputeViewInput): PlotComputeView {
    const { status, isStatusError, isAxesLayout, isComputeStarted } = input;
    // A text axes layout is a projection, not a PaCMAP compute.
    if (isAxesLayout) return 'plot';
    // A failed status refresh keeps the last status, so a saved plot stays on screen.
    if (status?.is_computed) return 'plot';
    // A started compute keeps running on the server when a status refresh fails.
    if (isComputeStarted) return 'computing';
    if (isStatusError) return 'error';
    if (status === undefined) return 'checking';
    return isLargeCollection(status.embedding_count) ? 'prompt' : 'computing';
}

export function isPlotRequestEnabled(view: PlotComputeView): boolean {
    return view === 'computing' || view === 'plot';
}

function isLargeCollection(embeddingCount: number | null): boolean {
    // An unknown count must not skip the prompt.
    if (embeddingCount === null) return true;
    return embeddingCount >= PLOT_COMPUTE_CONFIRM_THRESHOLD;
}
