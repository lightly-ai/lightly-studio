import { writable, type Writable } from 'svelte/store';
import type { ViewportState } from 'embedding-atlas/svelte';
import type { ToolMode } from '../PlotToolPill/selectionTool';

export interface PlotViewState {
    hiddenKeys: Writable<Set<string>>;
    viewport: Writable<ViewportState | null>;
    activeTool: Writable<ToolMode>;
    selectedColorByKey: Writable<string | null>;
}

// The plot unmounts when it closes. The view state lives at module scope, per collection, so a
// reopened plot shows the hidden classes, zoom, tool and color-by key the user left it with.
const createViewState = (): PlotViewState => ({
    hiddenKeys: writable(new Set<string>()),
    viewport: writable<ViewportState | null>(null),
    activeTool: writable<ToolMode>('pan'),
    selectedColorByKey: writable<string | null>(null)
});

const viewStateByCollection = new Map<string, PlotViewState>();

export function usePlotViewState(collectionId: string): PlotViewState {
    let state = viewStateByCollection.get(collectionId);
    if (!state) {
        state = createViewState();
        viewStateByCollection.set(collectionId, state);
    }
    return state;
}

// Forgets the view state of `collectionId`, so the next plot starts fresh.
export function clearPlotViewState(collectionId: string) {
    viewStateByCollection.delete(collectionId);
}
