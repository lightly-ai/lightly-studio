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
    if (isStatusError) return 'error';
    if (status === undefined) return isComputeStarted ? 'computing' : 'checking';
    if (status.is_computed) return 'plot';
    // The status has a count whenever no plot is saved.
    const isLarge = (status.embedding_count ?? 0) >= PLOT_COMPUTE_CONFIRM_THRESHOLD;
    if (isLarge && !isComputeStarted) return 'prompt';
    return 'computing';
}

export function isPlotRequestEnabled(view: PlotComputeView): boolean {
    return view === 'computing' || view === 'plot';
}

export function formatElapsed(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
