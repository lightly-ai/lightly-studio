import { ApiError } from './ApiError';
import { client } from './lightly_studio_local/client.gen';

/**
 * Makes each HTTP error of the API client an `ApiError`, and rejects on all other failures.
 *
 * Since 0.99, the client returns each failure as `{ error }` if `throwOnError` is not set. A
 * failure without an HTTP error response, such as a network error, an abort or a parse error,
 * rejects as it did before 0.99.
 */
export const registerApiErrorInterceptor = (): void => {
    client.interceptors.error.use((error, response) => {
        if (!response || response.ok) {
            throw error;
        }
        return ApiError.fromResponseBody(error, response.status);
    });
};
