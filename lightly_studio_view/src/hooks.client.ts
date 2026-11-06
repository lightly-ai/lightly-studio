import { client } from '$lib/api/lightly_studio_local/client.gen';

/**
 * Keeps the HTTP status on API errors, and rejects on transport failures.
 *
 * Registered here, not in a component, so it also covers requests from `load` functions, which
 * run before the root layout. Since 0.99, the client returns a failure without a response as
 * `{ error }`. We throw it, as the client did before.
 */
client.interceptors.error.use((error: unknown, response: Response | undefined) => {
    if (!response) {
        throw error;
    }
    if (typeof error === 'object' && error !== null) {
        return Object.assign(error, { status: response.status });
    }
    return error;
});
