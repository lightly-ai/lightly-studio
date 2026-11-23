import { ApiError } from './ApiError';

const MAX_QUERY_RETRIES = 3;

const isClientError = (error: Error) =>
    error instanceof ApiError && error.status >= 400 && error.status < 500;

/** Retries network errors and server errors (5xx) up to 3 times, but not client errors (4xx). */
export const shouldRetryQuery = (failureCount: number, error: Error): boolean =>
    !isClientError(error) && failureCount < MAX_QUERY_RETRIES;
