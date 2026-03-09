import { getGroupComponentsByGroupIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GroupComponentView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useGroupComponents = ({
	groupId
}: {
	groupId: string;
}): { groupComponents: CreateQueryResult<GroupComponentView[], Error>; refetch: () => void } => {
	const readGroupComponents = getGroupComponentsByGroupIdOptions({
		path: {
			group_id: groupId
		}
	});
	const client = useQueryClient();
	const groupComponents = createQuery(readGroupComponents);
	const refetch = () => {
		client.invalidateQueries({ queryKey: readGroupComponents.queryKey });
	};

	return {
		refetch,
		groupComponents
	};
};
