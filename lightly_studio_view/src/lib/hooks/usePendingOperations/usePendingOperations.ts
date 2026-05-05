type PendingOperation = {
    operation: string;
    isPending: boolean;
};

type UsePendingOperationsProps = {
    operationPrefix: string;
    onPendingChange?: (pendingOperation: PendingOperation) => void;
};

/**
 * Creates and tracks deterministic pending operation ids for async operations.
 *
 * Each call to `startPending` emits a unique operation id and a pending event.
 * The operation id must be passed to `endPending` to emit the corresponding completion event.
 *
 * @param operationPrefix Prefix used to generate stable operation ids.
 * @param onPendingChange Optional callback invoked whenever an operation starts or stops being pending.
 * @returns Operation lifecycle helpers to start, end, or reset pending operations.
 */
export const usePendingOperations = ({
    operationPrefix,
    onPendingChange
}: UsePendingOperationsProps) => {
    const pendingOperations = new Set<string>();
    let pendingOperationCounter = 0;

    const setPending = (pendingOperation: PendingOperation) => {
        onPendingChange?.(pendingOperation);
    };

    /**
     * Starts a pending operation and returns its generated operation id.
     *
     * @returns The generated operation id that identifies the pending operation.
     */
    const startPending = () => {
        pendingOperationCounter += 1;
        const operation = `${operationPrefix}-${pendingOperationCounter}`;
        pendingOperations.add(operation);
        setPending({ operation, isPending: true });
        return operation;
    };

    /**
     * Ends a pending operation for the given operation id.
     * No-op when the operation id is unknown.
     *
     * @param operation Operation id previously returned by `startPending`.
     */
    const endPending = (operation: string) => {
        if (!pendingOperations.has(operation)) return;

        pendingOperations.delete(operation);
        setPending({ operation, isPending: false });
    };

    /**
     * Ends all currently pending operations and clears internal state.
     */
    const resetPending = () => {
        for (const operation of pendingOperations) {
            setPending({ operation, isPending: false });
        }

        pendingOperations.clear();
    };

    return {
        startPending,
        endPending,
        resetPending
    };
};
