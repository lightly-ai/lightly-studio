import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkflowGridFilter } from './useWorkflowGridFilter.svelte';

const { workflow, refreshIfOlderThan } = vi.hoisted(() => ({
    workflow: { projectId: null as string | null },
    refreshIfOlderThan: vi.fn()
}));

vi.mock('$lib/hooks/useWorkflowProject/useWorkflowProject.svelte', () => ({
    useWorkflowProject: () => ({
        get projectId() {
            return workflow.projectId;
        }
    })
}));

vi.mock('$lib/hooks/useWorkflowStatusCounts/useWorkflowStatusCounts.svelte', () => ({
    useWorkflowStatusCounts: () => ({ counts: null, refreshIfOlderThan })
}));

describe('useWorkflowGridFilter', () => {
    beforeEach(() => {
        workflow.projectId = null;
        refreshIfOlderThan.mockClear();
    });

    it('filters by the selected states when the dataset has a project', () => {
        workflow.projectId = 'project-1';
        const grid = useWorkflowGridFilter(() => 'collection-1');

        expect(grid.statesToFilter(['accepted'])).toEqual(['accepted']);
        expect(grid.statesToFilter([])).toBeUndefined();
    });

    it('does not filter by workflow state without a project', () => {
        const grid = useWorkflowGridFilter(() => 'collection-1');

        expect(grid.statesToFilter(['accepted'])).toBeUndefined();
    });

    it('refreshes the counts once a grid reload finishes', () => {
        vi.spyOn(Date, 'now').mockReturnValueOnce(1000).mockReturnValueOnce(2000);
        const grid = useWorkflowGridFilter(() => 'collection-1');

        grid.onGridRefetching(true);
        expect(refreshIfOlderThan).not.toHaveBeenCalled();
        grid.onGridRefetching(false);

        expect(refreshIfOlderThan).toHaveBeenCalledExactlyOnceWith(1000);
    });
});
