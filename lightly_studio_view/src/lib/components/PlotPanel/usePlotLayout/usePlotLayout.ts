import { derived, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { ProjectionAxes } from '$lib/api/lightly_studio_local';
import { embedTextAxes } from '../PlotTextAxesInputs/embedTextAxes';
import { createEmptyTextAxesDraft } from '../PlotTextAxesInputs/textAxesDraft';

export type PlotLayout = 'pacmap' | 'text';

// The plot shows the PaCMAP layout. In Text mode it shows the projection onto two text axes,
// once all four texts are committed. The state lives at module scope, per collection: the plot
// unmounts when it closes, but a saved region keeps its axes, so a reopened plot must show the
// layout of that region.
const createLayoutState = () => ({
    plotLayout: writable<PlotLayout>('pacmap'),
    textAxesDraft: writable(createEmptyTextAxesDraft()),
    committedAxes: writable<ProjectionAxes | null>(null),
    isEmbeddingAxes: writable(false)
});

const layoutStateByCollection = new Map<string, ReturnType<typeof createLayoutState>>();

export function usePlotLayout(collectionId: string) {
    let state = layoutStateByCollection.get(collectionId);
    if (!state) {
        state = createLayoutState();
        layoutStateByCollection.set(collectionId, state);
    }
    const { plotLayout, textAxesDraft, committedAxes, isEmbeddingAxes } = state;

    const plotAxes = derived([plotLayout, committedAxes], ([$plotLayout, $committedAxes]) =>
        $plotLayout === 'text' ? $committedAxes : null
    );
    const isAwaitingAxes = derived(
        [plotLayout, committedAxes],
        ([$plotLayout, $committedAxes]) => $plotLayout === 'text' && $committedAxes === null
    );

    const commitTextAxes = async (textAxes: Parameters<typeof embedTextAxes>[1]) => {
        isEmbeddingAxes.set(true);
        try {
            committedAxes.set(await embedTextAxes(collectionId, textAxes));
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to embed the axis texts.');
        } finally {
            isEmbeddingAxes.set(false);
        }
    };

    return { plotLayout, textAxesDraft, isEmbeddingAxes, plotAxes, isAwaitingAxes, commitTextAxes };
}

// Forgets the layout of `collectionId`, so the next plot starts in PaCMAP.
export function clearPlotLayout(collectionId: string) {
    layoutStateByCollection.delete(collectionId);
}
