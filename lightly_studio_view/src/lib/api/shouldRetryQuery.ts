import { ApiError } from './ApiError';
import { NoRetryError } from './NoRetryError';

const MAX_QUERY_RETRIES = 3;

const isClientError = (error: Error) =>
    error instanceof ApiError && error.status >= 400 && error.status < 500;

/**
 * Retries network errors and server errors (5xx) up to 3 times, but not client errors (4xx) or a
 * `NoRetryError`.
 */
export const shouldRetryQuery = (failureCount: number, error: Error): boolean =>
    !(error instanceof NoRetryError) && !isClientError(error) && failureCount < MAX_QUERY_RETRIES;
