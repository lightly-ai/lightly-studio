import { derived, writable } from 'svelte/store';
import type { PendingChange } from './pendingChange';

/**
 * Creates local pending-state stores for async operations.
 *
 * Tracks unique operation names that are currently pending and exposes:
 * - `pendingOperations`: the list of pending operation identifiers
 * - `isPending`: `true` when at least one operation is pending
 * - `handlePendingChange`: updater for adding/removing operations based on a `PendingChange`
 */
export const usePendingState = () => {
    const pendingOperations = writable<string[]>([]);
    const isPending = derived(pendingOperations, ($operations) => $operations.length > 0);

    const handlePendingChange = (pendingChange: PendingChange) => {
        pendingOperations.update((operations) => {
            if (pendingChange.isPending) {
                if (!operations.includes(pendingChange.operation)) {
                    return [...operations, pendingChange.operation];
                }

                return operations;
            }

            return operations.filter((operation) => operation !== pendingChange.operation);
        });
    };

    return {
        pendingOperations,
        isPending,
        handlePendingChange
    };
};
