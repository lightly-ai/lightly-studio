import { derived, writable } from 'svelte/store';

const minimumConfidence = writable(0);
const isConfidenceVisible = derived(
    minimumConfidence,
    (minimum) => (confidence: number | null | undefined) =>
        confidence == null || confidence >= minimum
);

export function useAnnotationConfidence() {
    return { minimumConfidence, isConfidenceVisible };
}
