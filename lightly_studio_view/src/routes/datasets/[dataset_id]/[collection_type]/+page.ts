import { goto } from '$app/navigation';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    // This route is only reached when the URL is incomplete (missing collection_id)
    // Redirect to home
    goto(routeHelpers.toHome());
    return new Promise(() => {});
};
