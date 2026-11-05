import { client } from '$lib/api/lightly_studio_local/client.gen';

/**
 * Keeps the HTTP status on API errors.
 *
 * Registered here, so it also covers requests from `load` functions, which run before the root
 * layout. Network, abort and parse errors are thrown. An HTTP error body that is not an object,
 * for example plain text, is wrapped as `{ error, status }`.
 */
client.interceptors.error.use((error: unknown, response: Response | undefined) => {
    if (!response || response.ok) {
        throw error;
    }
    if (typeof error === 'object' && error !== null) {
        return Object.assign(error, { status: response.status });
    }
    return { error, status: response.status };
});
