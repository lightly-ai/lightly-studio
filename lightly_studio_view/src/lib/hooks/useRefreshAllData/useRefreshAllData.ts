import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { loadCollectionTags } from '$lib/hooks';

interface UseRefreshAllDataReturn {
    refreshAllData: (collectionId: string) => Promise<void>;
}

/** Refetches all data, e.g. after it changed outside the GUI. Tags have their own store. */
export function useRefreshAllData(): UseRefreshAllDataReturn {
    const client = useQueryClient();

    const refreshAllData = async (collectionId: string) => {
        await Promise.all([
            // Never reject, so callers don't mistake a failed refresh for a failed action.
            loadCollectionTags(collectionId).catch(() => toast.error('Failed to refresh tags.')),
            client.invalidateQueries()
        ]);
    };

    return { refreshAllData };
}
