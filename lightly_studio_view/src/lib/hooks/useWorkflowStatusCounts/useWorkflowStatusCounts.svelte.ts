import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import type { WorkflowStatus } from '$lib/api/lightly_studio_local';
import { getWorkflowStatusCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export type WorkflowStatusCounts = Partial<Record<WorkflowStatus, number>>;

type Params = {
    collectionId: string;
    /** The dataset's workflow project. Without one, no counts request is made. */
    projectId: string | null;
};

/**
 * The project-wide sample count of each workflow status option. The counts ignore the
 * grid filters, so one query covers every option. They are not polled: the grid calls
 * `refreshIfOlderThan` when it reloads.
 */
export const useWorkflowStatusCounts = (getParams: () => Params) => {
    const client = useQueryClient();
    const options = () =>
        getWorkflowStatusCountsOptions({ path: { collection_id: getParams().collectionId } });
    const query = createQuery(() => ({
        ...options(),
        enabled: Boolean(getParams().projectId)
    }));

    return {
        /** The count per option, or null while loading or without a project. */
        get counts(): WorkflowStatusCounts | null {
            return query.data?.counts ?? null;
        },
        /**
         * Refetch the counts if they are older than `time` (ms since epoch), for example
         * the start of a grid reload. Joins a fetch that is already in flight.
         */
        refreshIfOlderThan(time: number) {
            if (!getParams().projectId || query.dataUpdatedAt >= time) {
                return;
            }
            client.invalidateQueries({ queryKey: options().queryKey }, { cancelRefetch: false });
        }
    };
};
