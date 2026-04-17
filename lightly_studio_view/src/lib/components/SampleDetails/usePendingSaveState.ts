import { derived, writable } from 'svelte/store';
import type { SavePendingChange } from './savePendingChange';

export const usePendingSaveState = () => {
    const pendingSaveTokens = writable<string[]>([]);
    const isSavePending = derived(pendingSaveTokens, ($tokens) => $tokens.length > 0);

    const handleSavePendingChange = (pendingChange: SavePendingChange) => {
        pendingSaveTokens.update((tokens) => {
            if (pendingChange.isPending) {
                if (!tokens.includes(pendingChange.token)) {
                    return [...tokens, pendingChange.token];
                }

                return tokens;
            }

            return tokens.filter((token) => token !== pendingChange.token);
        });
    };

    return {
        pendingSaveTokens,
        isSavePending,
        handleSavePendingChange
    };
};
