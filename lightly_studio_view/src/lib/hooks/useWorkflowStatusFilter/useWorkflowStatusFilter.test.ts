import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useWorkflowStatusFilter } from './useWorkflowStatusFilter';

describe('useWorkflowStatusFilter', () => {
    beforeEach(() => {
        useWorkflowStatusFilter('collection-1').clearWorkflowStates();
        useWorkflowStatusFilter('collection-2').clearWorkflowStates();
    });

    it('starts with no option selected', () => {
        const { selectedWorkflowStates } = useWorkflowStatusFilter('collection-1');

        expect(get(selectedWorkflowStates)).toEqual([]);
    });

    it('toggles options on and off', () => {
        const { selectedWorkflowStates, toggleWorkflowState } =
            useWorkflowStatusFilter('collection-1');

        toggleWorkflowState('in_review');
        toggleWorkflowState('not_in_workflow');
        expect(get(selectedWorkflowStates)).toEqual(['in_review', 'not_in_workflow']);

        toggleWorkflowState('in_review');
        expect(get(selectedWorkflowStates)).toEqual(['not_in_workflow']);
    });

    it('keeps the selection of each collection apart', () => {
        useWorkflowStatusFilter('collection-1').setWorkflowStates(['accepted']);

        expect(get(useWorkflowStatusFilter('collection-1').selectedWorkflowStates)).toEqual([
            'accepted'
        ]);
        expect(get(useWorkflowStatusFilter('collection-2').selectedWorkflowStates)).toEqual([]);
    });

    it('clears the selection', () => {
        const { selectedWorkflowStates, setWorkflowStates, clearWorkflowStates } =
            useWorkflowStatusFilter('collection-1');
        setWorkflowStates(['rework', 'accepted']);

        clearWorkflowStates();

        expect(get(selectedWorkflowStates)).toEqual([]);
    });
});
