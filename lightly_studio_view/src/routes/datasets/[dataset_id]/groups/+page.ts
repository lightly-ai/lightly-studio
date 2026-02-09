import type { PageLoad } from './$types';
import type { Group } from '../../../../../api/groups/+server';

export const load: PageLoad = async ({ fetch }) => {
    const response = await fetch('http://localhost:5173/api/groups');
    const data = await response.json();

    return {
        groups: data.groups as Group[],
        total: data.total as number
    };
};
