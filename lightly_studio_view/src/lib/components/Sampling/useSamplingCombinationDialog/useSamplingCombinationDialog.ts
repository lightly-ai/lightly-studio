import { derived, get, writable, type Readable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSamplingDialog } from '$lib/hooks/useSamplingDialog/useSamplingDialog';
import { isStrategyInstanceValid, type StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { useSubmitCombinationSelection } from '$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useSelectionFilter } from './useSelectionFilter';

interface UseSamplingCombinationDialogParams {
    getCollectionId: () => string;
    getIsVideoCollection: () => boolean;
    instances: Readable<StrategyInstance[]>;
    onSubmitSuccess: () => void;
}

export function useSamplingCombinationDialog({
    getCollectionId,
    getIsVideoCollection,
    instances,
    onSubmitSuccess
}: UseSamplingCombinationDialogParams) {
    const { tags, loadTags, setTagSelected } = useTags({
        collection_id: getCollectionId(),
        kind: ['sample']
    });

    const { filteredSampleCount } = useGlobalStorage();
    const { closeSamplingDialog } = useSamplingDialog();
    const { buildSelectionFilter } = useSelectionFilter(getIsVideoCollection);

    const { isSubmitting, loadingMessage, submit } = useSubmitCombinationSelection({
        tags,
        setTagSelected,
        loadTags,
        closeSelectionDialog: closeSamplingDialog
    });

    const nSamplesToSelect = writable<number>(10);
    const selectionResultTagName = writable('');

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

    function resetForm() {
        onSubmitSuccess();
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
        nSamplesToSelect,
        selectionResultTagName,
        filteredSampleCount,
        noSamples,
        notEnoughSamples,
        sampleCountLabel,
        isFormValid,
        isSubmitting,
        loadingMessage,
        handleFormSubmit
    };
}
