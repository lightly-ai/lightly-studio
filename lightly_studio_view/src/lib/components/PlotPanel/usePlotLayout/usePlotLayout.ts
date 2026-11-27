import { derived, get, writable } from 'svelte/store';
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
    appliedTextAxes: writable<Parameters<typeof embedTextAxes>[1] | null>(null),
    isEmbeddingAxes: writable(false)
});

const layoutStateByCollection = new Map<string, ReturnType<typeof createLayoutState>>();

export function usePlotLayout(collectionId: string) {
    let state = layoutStateByCollection.get(collectionId);
    if (!state) {
        state = createLayoutState();
        layoutStateByCollection.set(collectionId, state);
    }
    const { plotLayout, textAxesDraft, committedAxes, appliedTextAxes, isEmbeddingAxes } = state;

    const plotAxes = derived([plotLayout, committedAxes], ([$plotLayout, $committedAxes]) =>
        $plotLayout === 'text' ? $committedAxes : null
    );

    // Returns false when the texts fail to embed. The committed axes then stay as they are.
    const commitTextAxes = async (textAxes: Parameters<typeof embedTextAxes>[1]) => {
        if (get(isEmbeddingAxes)) return false;
        isEmbeddingAxes.set(true);
        try {
            committedAxes.set(await embedTextAxes(collectionId, textAxes));
            appliedTextAxes.set(textAxes);
            plotLayout.set('text');
            return true;
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to embed the axis texts.');
            return false;
        } finally {
            isEmbeddingAxes.set(false);
        }
    };

    return {
        plotLayout,
        textAxesDraft,
        appliedTextAxes,
        isEmbeddingAxes,
        plotAxes,
        commitTextAxes
    };
}

// Forgets the layout of `collectionId`, so the next plot starts in PaCMAP.
export function clearPlotLayout(collectionId: string) {
    layoutStateByCollection.delete(collectionId);
}
