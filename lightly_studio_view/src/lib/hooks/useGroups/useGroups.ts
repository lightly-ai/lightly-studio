import { type GetAllGroupsData, type Options } from '$lib/api/lightly_studio_local';
import { getAllGroupsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

/**
 * Hook for fetching and managing groups data from the API.
 *
 * Each group includes the first sample (image or video) for display in the grid.
 *
 * @param options - Options for the groups query, including path parameters like collection_id
 * @returns An object containing:
 *   - `groups`: A Svelte query result store with the groups data
 *   - `refetch`: Function to manually refetch the groups data
 *
 * @example
 * ```ts
 * const { groups, refetch } = useGroups({
 *     path: { collection_id: 'abc123' }
 * });
 *
 * // Access groups data
 * $groups.data // Array of group objects, each with first_sample_image or first_sample_video
 * $groups.isLoading // Loading state
 * $groups.error // Error if fetch failed
 *
 * // Each group object contains:
 * // - sample_id: UUID of the group
 * // - sample: Group sample metadata
 * // - first_sample_image: First image in the group (if group contains images)
 * // - first_sample_video: First video in the group (if group contains videos)
 *
 * // Manually refetch groups
 * refetch();
 * ```
 */
export const useGroups = (options: Options<GetAllGroupsData>) => {
    const getGroups = getAllGroupsOptions(options);
    const client = useQueryClient();
    const groups = createQuery(getGroups);
    const refetch = () => {
        client.invalidateQueries({ queryKey: getGroups.queryKey });
    };

    return {
        refetch,
        groups
    };
};
