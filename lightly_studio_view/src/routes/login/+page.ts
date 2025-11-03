import { redirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
    // Only check auth in browser (localStorage not available on server)
    if (browser) {
        const token = localStorage.getItem('auth_token');
        if (token) {
            // User is already authenticated, redirect to home
            redirect(307, '/');
        }
    }

    return {};
};
