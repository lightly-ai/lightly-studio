import { untrack } from 'svelte';
import type { WorkflowStatus } from '$lib/api/lightly_studio_local';
import { useWorkflowProject } from '$lib/hooks/useWorkflowProject/useWorkflowProject.svelte';
import { useWorkflowStatusCounts } from '$lib/hooks/useWorkflowStatusCounts/useWorkflowStatusCounts.svelte';
import { trackGridReload } from '$lib/hooks/useWorkflowStatusCounts/trackGridReload';

/**
 * The workflow status filter of a sample grid (images or MCAP sequences).
 *
 * The filter applies only when the dataset has a workflow project, so a dataset without one
 * runs no workflow SQL. The status counts are not polled: they refresh when the grid reloads,
 * so a state change made elsewhere shows up once the user is back on the grid.
 */
export const useWorkflowGridFilter = (getCollectionId: () => string) => {
    const project = useWorkflowProject(getCollectionId);
    const statusCounts = useWorkflowStatusCounts(() => ({
        collectionId: getCollectionId(),
        projectId: project.projectId
    }));
    const onGridReload = trackGridReload();

    return {
        /** The selected states to send with the grid filter, or undefined for no filter. */
        statesToFilter(selected: WorkflowStatus[]): WorkflowStatus[] | undefined {
            return project.projectId && selected.length > 0 ? selected : undefined;
        },
        /**
         * Feed the grid query's refetch state on every change. A refetch of the same grid
         * query, not a filter change (a new query) and not the next page. Toggling a filter
         * leaves the project-wide counts as they are.
         */
        onGridRefetching(isRefetching: boolean) {
            const reloadStartedAt = onGridReload(isRefetching, Date.now());
            if (reloadStartedAt !== null) {
                untrack(() => statusCounts.refreshIfOlderThan(reloadStartedAt));
            }
        }
    };
};
