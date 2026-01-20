import { redirect } from '@sveltejs/kit';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    // This route is only reached when the URL is incomplete (missing collection_id)
    // Redirect to home
    throw redirect(307, routeHelpers.toHome());
};
