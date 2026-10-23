import { createQuery } from '@tanstack/svelte-query';
import { getAssistedLabelingStatusOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getAssistedLabelingDisabledReason } from './getAssistedLabelingDisabledReason';

interface UseAssistedLabelingStatusReturn {
    readonly disabledReason: string | null;
}

export const useAssistedLabelingStatus = (): UseAssistedLabelingStatusReturn => {
    const query = createQuery(() => getAssistedLabelingStatusOptions());
    const disabledReason = $derived(
        getAssistedLabelingDisabledReason({ status: query.data, isError: query.isError })
    );

    return {
        get disabledReason() {
            return disabledReason;
        }
    };
};
