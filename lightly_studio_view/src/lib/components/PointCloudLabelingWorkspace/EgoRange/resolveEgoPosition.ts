import type { Vector3 } from '../domain';

interface ResolveEgoPositionInput {
    canQuery: boolean;
    isError: boolean;
    position: readonly number[] | null | undefined;
}

/**
 * Returns the ego position, `null` if it is unknown, or `undefined` while it loads or is not
 * requested. A failed request counts as unknown, so the user sees a notice.
 */
export function resolveEgoPosition({
    canQuery,
    isError,
    position
}: ResolveEgoPositionInput): Vector3 | null | undefined {
    if (!canQuery) return undefined;
    if (isError) return null;
    if (!position) return position;
    return [position[0], position[1], position[2]];
}
