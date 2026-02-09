import type { PageLoad } from './$types';
import type { Group } from '../../../../../api/groups/+server';

export const load: PageLoad = async ({ fetch, url }) => {
    const apiUrl = new URL('/api/groups', url.origin);
    apiUrl.searchParams.set('offset', '0');
    apiUrl.searchParams.set('limit', '10');

    const response = await fetch(apiUrl.toString());
    const data = await response.json();

    return {
        initialGroups: data.groups as Group[],
        total: data.total as number,
        hasMore: data.hasMore as boolean
    };
};
