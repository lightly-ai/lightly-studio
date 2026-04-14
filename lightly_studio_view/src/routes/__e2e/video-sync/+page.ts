import { dev } from '$app/environment';
import { error } from '@sveltejs/kit';

export const load = () => {
    if (!dev) {
        throw error(404, 'Not found');
    }

    return {};
};
