import { redirect } from '@sveltejs/kit';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    // Catch-all route: redirect any unmatched paths to home
    // This handles typos like /datas, /dataset, /invalid-path, etc.
    throw redirect(307, routeHelpers.toHome());
};
