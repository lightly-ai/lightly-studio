import { readonly, writable } from 'svelte/store';

const hoveredSampleId = writable<string | null>(null);

/**
 * The sample under the mouse in a grid. The embedding plot highlights its point.
 */
export function useHoveredSample() {
    const setHoveredSampleId = (sampleId: string) => hoveredSampleId.set(sampleId);

    // Clears only the given sample, so leaving one tile cannot clear the tile entered next.
    const clearHoveredSampleId = (sampleId: string) =>
        hoveredSampleId.update((current) => (current === sampleId ? null : current));

    return {
        hoveredSampleId: readonly(hoveredSampleId),
        setHoveredSampleId,
        clearHoveredSampleId
    };
}
