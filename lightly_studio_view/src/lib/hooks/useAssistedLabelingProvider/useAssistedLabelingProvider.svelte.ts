import { fromStore } from 'svelte/store';
import { useAssistedLabelingProviders } from '$lib/hooks/useAssistedLabelingProviders';
import { useSettings } from '$lib/hooks/useSettings';
import { getAssistedLabelingTools } from './getAssistedLabelingTools';

export const useAssistedLabelingProvider = () => {
    const { query } = useAssistedLabelingProviders();
    const settings = fromStore(useSettings().settingsStore);
    const provider = $derived(
        query.data?.find((p) => p.provider_id === settings.current.assisted_labeling_provider)
    );
    const tools = $derived(getAssistedLabelingTools({ provider, isError: query.isError }));

    return {
        get tools() {
            return tools;
        }
    };
};
