type PendingSaveOperation = {
    token: string;
    isPending: boolean;
};

type UsePendingSaveTokensProps = {
    tokenPrefix: string;
    onPendingChange?: (pendingOperation: PendingSaveOperation) => void;
};

export const usePendingSaveTokens = ({
    tokenPrefix,
    onPendingChange
}: UsePendingSaveTokensProps) => {
    const pendingSaveTokens = new Set<string>();
    let pendingSaveTokenCounter = 0;

    const setPending = (pendingOperation: PendingSaveOperation) => {
        onPendingChange?.(pendingOperation);
    };

    // Manage pending save operations with deterministic token lifecycle events.
    const startPending = () => {
        pendingSaveTokenCounter += 1;
        const token = `${tokenPrefix}-${pendingSaveTokenCounter}`;
        pendingSaveTokens.add(token);
        setPending({ token, isPending: true });
        return token;
    };

    const endPending = (token: string) => {
        if (!pendingSaveTokens.has(token)) return;

        pendingSaveTokens.delete(token);
        setPending({ token, isPending: false });
    };

    const resetPending = () => {
        for (const token of pendingSaveTokens) {
            setPending({ token, isPending: false });
        }

        pendingSaveTokens.clear();
    };

    return {
        startPending,
        endPending,
        resetPending
    };
};
