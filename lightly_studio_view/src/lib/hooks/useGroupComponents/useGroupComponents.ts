import { getGroupComponentsByGroupIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GroupComponentView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useGroupComponents = ({
    getGroupId
}: {
    getGroupId: () => string;
}): { groupComponents: CreateQueryResult<GroupComponentView[], Error>; refetch: () => void } => {
    const client = useQueryClient();
    const groupComponents = createQuery(() =>
        getGroupComponentsByGroupIdOptions({ path: { group_id: getGroupId() } })
    );
    const refetch = () => {
        client.invalidateQueries({
            queryKey: getGroupComponentsByGroupIdOptions({ path: { group_id: getGroupId() } })
                .queryKey
        });
    };

    return {
        refetch,
        groupComponents
    };
};
