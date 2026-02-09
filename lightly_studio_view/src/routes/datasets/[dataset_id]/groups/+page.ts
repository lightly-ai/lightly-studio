import type { PageLoad } from './$types';
import type { Group } from '../../../../../api/groups/+server';

export const load: PageLoad = async ({ fetch, url }) => {
    // Load enough items to fill the screen and enable scrolling
    // Assuming grid with 280px min width + gap, roughly 4-5 columns on typical screen
    // and ~600px visible height means ~2-3 rows visible, so load 20 items (4-5 rows)
    const apiUrl = new URL('/api/groups', url.origin);
    apiUrl.searchParams.set('offset', '0');
    apiUrl.searchParams.set('limit', '20');

    const response = await fetch(apiUrl.toString());
    const data = await response.json();

    return {
        initialGroups: data.groups as Group[],
        total: data.total as number,
        hasMore: data.hasMore as boolean
    };
};
