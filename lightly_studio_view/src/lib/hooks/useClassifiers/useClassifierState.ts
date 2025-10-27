import { writable } from 'svelte/store';

// Classifier-specific state stores
const classifierSamples = writable<{
    positiveSampleIds: string[];
    negativeSampleIds: string[];
} | null>(null);

// Separate classifier selection variables to avoid interference with main grid
const classifierSelectedSampleIds = writable<Set<string>>(new Set());

export function useClassifierState() {
    // Classifier samples methods
    const setClassifierSamples = (
        samples: {
            positiveSampleIds: string[];
            negativeSampleIds: string[];
        } | null
    ) => {
        classifierSamples.set(samples);
    };

    const clearClassifierSamples = () => {
        classifierSamples.set(null);
    };

    // Classifier-specific selection methods
    const toggleClassifierSampleSelection = (sampleId: string) => {
        classifierSelectedSampleIds.update((state) => {
            if (state.has(sampleId)) {
                state.delete(sampleId);
            } else {
                state.add(sampleId);
            }
            return state;
        });
    };

    const clearClassifierSelectedSamples = () => {
        classifierSelectedSampleIds.update((state) => {
            state.clear();
            return state;
        });
    };

    return {
        // Stores
        classifierSamples,
        classifierSelectedSampleIds,

        // Methods
        setClassifierSamples,
        clearClassifierSamples,
        toggleClassifierSampleSelection,
        clearClassifierSelectedSamples
    };
}
