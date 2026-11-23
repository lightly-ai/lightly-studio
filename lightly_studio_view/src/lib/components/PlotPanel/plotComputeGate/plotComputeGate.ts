import type { Embeddings2dStatus } from '$lib/api/lightly_studio_local';

// A first PaCMAP compute above this many embeddings can run for minutes, so the panel asks first.
export const PLOT_COMPUTE_CONFIRM_THRESHOLD = 250_000;

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
    // A started compute keeps running on the server when a status refresh fails.
    if (isComputeStarted) return status?.is_computed ? 'plot' : 'computing';
    if (isStatusError) return 'error';
    if (status === undefined) return 'checking';
    if (status.is_computed) return 'plot';
    // The status has a count whenever no plot is saved.
    const isLarge = (status.embedding_count ?? 0) >= PLOT_COMPUTE_CONFIRM_THRESHOLD;
    return isLarge ? 'prompt' : 'computing';
}

export function isPlotRequestEnabled(view: PlotComputeView): boolean {
    return view === 'computing' || view === 'plot';
}
