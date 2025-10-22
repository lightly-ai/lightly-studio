import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';

/**
 * Helper function to handle cleanup when closing create classifier dialog
 */
export function handleCreateClassifierClose() {
    const { clearClassifierSamples, clearClassifierSelectedSamples } = useGlobalStorage();
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
export function handleRefineClassifierClose() {
    const { clearClassifierSelectedSamples } = useGlobalStorage();
    const { closeRefineClassifiersPanel } = useRefineClassifiersPanel();
    const showTrainingSamplesToggle = useSessionStorage<boolean>(
        'refine_classifier_show_training_samples',
        false
    );

    // Clear classifier selection state
    clearClassifierSelectedSamples();
    showTrainingSamplesToggle.set(false);

    // Close dialog
    closeRefineClassifiersPanel();
}
