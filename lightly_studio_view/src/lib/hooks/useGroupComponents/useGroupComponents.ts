import { getGroupComponentsByGroupIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    GetGroupComponentsByGroupIdError,
    GroupComponentView
} from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useGroupComponents = ({
    getGroupId
}: {
    getGroupId: () => string;
}): {
    groupComponents: CreateQueryResult<GroupComponentView[], GetGroupComponentsByGroupIdError>;
    refetch: () => void;
} => {
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
