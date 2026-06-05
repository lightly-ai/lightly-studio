import { derived, get, writable } from 'svelte/store';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useSamplingDialog } from '$lib/hooks/useSamplingDialog/useSamplingDialog';
import { isStrategyInstanceValid, useStrategyBuilder } from '$lib/hooks/useStrategyBuilder';
import { useSubmitCombinationSelection } from '$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

interface UseSamplingCombinationDialogParams {
    getCollectionId: () => string;
    getIsVideoCollection: () => boolean;
}

export function useSamplingCombinationDialog({
    getCollectionId,
    getIsVideoCollection
}: UseSamplingCombinationDialogParams) {
    const { tags, loadTags, setTagSelected } = useTags({
        collection_id: getCollectionId(),
        kind: ['sample']
    });

    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { filteredSampleCount } = useGlobalStorage();
    const { metadataInfo } = useMetadataFilters(getCollectionId());

    const {
        instances,
        addStrategy,
        duplicateStrategy,
        removeStrategy,
        resetStrategies,
        toggleExpand,
        updateParams
    } = useStrategyBuilder();

    const { closeSamplingDialog } = useSamplingDialog();

    const { isSubmitting, loadingMessage, submit } = useSubmitCombinationSelection({
        tags,
        setTagSelected,
        loadTags,
        closeSelectionDialog: closeSamplingDialog
    });

    const nSamplesToSelect = writable<number>(10);
    const selectionResultTagName = writable('');

    const metadataFieldNames = derived(metadataInfo, ($metadataInfo) =>
        $metadataInfo
            .filter((info) => info.type === 'integer' || info.type === 'float')
            .map((info) => info.name)
    );

    const hasMetadataFields = derived(metadataFieldNames, ($names) => $names.length > 0);

    const noSamples = derived(filteredSampleCount, ($count) => $count === 0);

    const notEnoughSamples = derived(
        [filteredSampleCount, nSamplesToSelect],
        ([$count, $n]) => $count > 0 && $n > $count
    );

    const sampleCountLabel = derived(
        filteredSampleCount,
        ($count) => `${$count} ${$count === 1 ? 'sample' : 'samples'}`
    );

    const isFormValid = derived(
        [instances, nSamplesToSelect, selectionResultTagName],
        ([$instances, $n, $name]) =>
            $instances.length > 0 &&
            $instances.every(isStrategyInstanceValid) &&
            $n > 0 &&
            $name.trim().length > 0
    );

    function buildSelectionFilter(): SamplingRequest['filter'] {
        if (getIsVideoCollection()) {
            const currentFilter = get(videoFilter);
            return currentFilter ? { ...currentFilter, filter_type: 'video' } : null;
        }
        const currentFilter = get(imageFilter);
        return currentFilter ? { ...currentFilter, filter_type: 'image' } : null;
    }

    function resetForm() {
        resetStrategies();
        nSamplesToSelect.set(10);
        selectionResultTagName.set('');
    }

    async function submitSelection() {
        const success = await submit({
            collectionId: getCollectionId(),
            isVideoCollection: getIsVideoCollection(),
            instances: get(instances),
            nSamplesToSelect: get(nSamplesToSelect),
            selectionResultTagName: get(selectionResultTagName),
            selectionFilter: buildSelectionFilter()
        });
        if (success) resetForm();
    }

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!get(isFormValid) || get(notEnoughSamples) || get(noSamples) || get(isSubmitting))
            return;
        void submitSelection();
    }

    return {
        tags,
        instances,
        nSamplesToSelect,
        selectionResultTagName,
        filteredSampleCount,
        metadataFieldNames,
        hasMetadataFields,
        noSamples,
        notEnoughSamples,
        sampleCountLabel,
        isFormValid,
        isSubmitting,
        loadingMessage,
        addStrategy,
        duplicateStrategy,
        removeStrategy,
        updateParams,
        toggleExpand,
        handleFormSubmit
    };
}
