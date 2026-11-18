import { createQuery } from '@tanstack/svelte-query';
import { getWorkflowProjectOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

/**
 * The labeling-workflow project of the collection's dataset.
 * `projectId` is null while loading, on error, and for a dataset without a project.
 */
export const useWorkflowProject = (getCollectionId: () => string) => {
    const query = createQuery(() => ({
        ...getWorkflowProjectOptions({ path: { collection_id: getCollectionId() } }),
        // A project is created rarely, so the answer stays valid for the whole visit.
        staleTime: Infinity
    }));
    return {
        get projectId(): string | null {
            return query.data?.project_id ?? null;
        }
    };
};
