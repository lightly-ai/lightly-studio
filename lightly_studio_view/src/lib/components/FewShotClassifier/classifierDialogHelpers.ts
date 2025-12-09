import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';

/**
 * Helper function to handle cleanup when closing create classifier dialog
 */
export function handleCreateClassifierClose() {
    const { clearClassifierSamples, clearClassifierSelectedSamples } = useClassifierState();
    const { closeCreateClassifiersPanel } = useCreateClassifiersPanel();

    // Clear all classifier-related state
    clearClassifierSamples();
    clearClassifierSelectedSamples();

    // Close dialog
    closeCreateClassifiersPanel();
}

/**
 * Helper function to handle cleanup when closing refine classifier dialog
 */
export function handleRefineClassifierClose(datasetId: string) {
    const { clearClassifierSelectedSamples } = useClassifierState();
    const { clearSelectedSamples } = useGlobalStorage();
    const { closeRefineClassifiersPanel } = useRefineClassifiersPanel();
    const showTrainingSamplesToggle = useSessionStorage<boolean>(
        'refine_classifier_show_training_samples',
        false
    );

    //Clear initial selection
    clearSelectedSamples(datasetId);
    // Clear classifier selection state
    clearClassifierSelectedSamples();
    showTrainingSamplesToggle.set(false);

    // Close dialog
    closeRefineClassifiersPanel();
}
