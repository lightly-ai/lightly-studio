import { derived, get, writable, type Readable } from 'svelte/store';
import type { WorkflowStatus } from '$lib/api/lightly_studio_local';

// Selected options by collection. They live in memory like the other dataset filters, and
// never in the URL.
const selectedByCollection = writable<Record<string, WorkflowStatus[]>>({});

interface UseWorkflowStatusFilterReturn {
    selectedWorkflowStates: Readable<WorkflowStatus[]>;
    toggleWorkflowState: (status: WorkflowStatus) => void;
    setWorkflowStates: (statuses: WorkflowStatus[]) => void;
    clearWorkflowStates: () => void;
}

/** The workflow status options selected in the image or MCAP sequence grid filter of a collection. */
export const useWorkflowStatusFilter = (collectionId: string): UseWorkflowStatusFilterReturn => {
    const selectedWorkflowStates = derived(
        selectedByCollection,
        ($selected) => $selected[collectionId] ?? []
    );
    const setWorkflowStates = (statuses: WorkflowStatus[]) =>
        selectedByCollection.update((selected) => ({ ...selected, [collectionId]: statuses }));
    const toggleWorkflowState = (status: WorkflowStatus) => {
        const current = get(selectedWorkflowStates);
        setWorkflowStates(
            current.includes(status)
                ? current.filter((selected) => selected !== status)
                : [...current, status]
        );
    };
    return {
        selectedWorkflowStates,
        toggleWorkflowState,
        setWorkflowStates,
        clearWorkflowStates: () => setWorkflowStates([])
    };
};
