import { derived, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { embedTextAxes } from '../PlotTextAxesInputs/embedTextAxes';
import { createEmptyTextAxesDraft } from '../PlotTextAxesInputs/textAxesDraft';

export type PlotLayout = 'pacmap' | 'text';

type TextLayout = Awaited<ReturnType<typeof embedTextAxes>>;

// The plot shows the PaCMAP layout. In Text mode it shows the projection onto two text axes and
// a marker for each corner phrase, once all four texts are committed. The state lives at module
// scope, per collection: the plot unmounts when it closes, but a saved region keeps its axes, so
// a reopened plot must show the layout of that region.
const createLayoutState = () => ({
    plotLayout: writable<PlotLayout>('pacmap'),
    textAxesDraft: writable(createEmptyTextAxesDraft()),
    committedTextLayout: writable<TextLayout | null>(null),
    isEmbeddingAxes: writable(false)
});

const layoutStateByCollection = new Map<string, ReturnType<typeof createLayoutState>>();

export function usePlotLayout(collectionId: string) {
    let state = layoutStateByCollection.get(collectionId);
    if (!state) {
        state = createLayoutState();
        layoutStateByCollection.set(collectionId, state);
    }
    const { plotLayout, textAxesDraft, committedTextLayout, isEmbeddingAxes } = state;

    const textLayout = derived([plotLayout, committedTextLayout], ([$plotLayout, $committed]) =>
        $plotLayout === 'text' ? $committed : null
    );
    const plotAxes = derived(textLayout, ($textLayout) => $textLayout?.axes ?? null);
    const plotMarkers = derived(textLayout, ($textLayout) => $textLayout?.markers ?? []);

    // Returns false when the texts fail to embed. The committed layout then stays as it is.
    const commitTextAxes = async (textAxes: Parameters<typeof embedTextAxes>[1]) => {
        isEmbeddingAxes.set(true);
        try {
            committedTextLayout.set(await embedTextAxes(collectionId, textAxes));
            return true;
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to embed the axis texts.');
            return false;
        } finally {
            isEmbeddingAxes.set(false);
        }
    };

    return { plotLayout, textAxesDraft, isEmbeddingAxes, plotAxes, plotMarkers, commitTextAxes };
}

// Forgets the layout of `collectionId`, so the next plot starts in PaCMAP.
export function clearPlotLayout(collectionId: string) {
    layoutStateByCollection.delete(collectionId);
}
