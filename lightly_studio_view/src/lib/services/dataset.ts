import type { paths } from '$lib/schema';
import createClient from 'openapi-fetch';
import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';

export const client = createClient<paths>({
    baseUrl: PUBLIC_LIGHTLY_STUDIO_API_URL,
    fetch: fetch
});

export default client;
