import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import { useFeatureFlags } from '$lib/hooks/useFeatureFlags/useFeatureFlags';

export const QUERY_FILTER_FEATURE_FLAG = 'query_filter';

interface UseQueryFilterReturn {
    isEnabled: Readable<boolean>;
    isEditing: Readable<boolean>;
    toggleEditing: () => void;
}

export function useQueryFilter(): UseQueryFilterReturn {
    const { featureFlags } = useFeatureFlags();
    const isEnabled = derived(featureFlags, ($flags) => $flags.includes(QUERY_FILTER_FEATURE_FLAG));
    const isEditing = writable(false);

    const toggleEditing = () => {
        if (!get(isEnabled)) {
            return;
        }
        isEditing.update((current) => !current);
    };

    return {
        isEnabled,
        isEditing: readonly(isEditing),
        toggleEditing
    };
}
