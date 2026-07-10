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

function computePercentage(count: number, total: number): number {
    return total > 0 ? Math.round((count / total) * 100) : 0;
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

    const nSamplesToSelect = writable<number | null>(10);
    // Null means the user hasn't explicitly typed a percentage; percentageToSelect
    // then derives reactively from nSamplesToSelect and filteredSampleCount so that
    // the display stays correct when filteredSampleCount loads after mount.
    // A non-null value locks the display to what the user typed, preventing
    // background filteredSampleCount updates (e.g. grid refetches) from overwriting it.
    const userEnteredPercentage = writable<number | null>(null);

    const percentageToSelect = derived(
        [nSamplesToSelect, filteredSampleCount, userEnteredPercentage],
        ([$n, $total, $userPct]) => {
            if ($userPct !== null) return $userPct;
            if ($n === null) return null;
            return computePercentage($n, $total);
        }
    );
    const selectionResultTagName = writable('');

    function updateAbsolute(count: number) {
        if (!Number.isFinite(count)) {
            nSamplesToSelect.set(null);
            userEnteredPercentage.set(null);
            return;
        }
        nSamplesToSelect.set(count);
        userEnteredPercentage.set(null); // let percentage re-derive from count
    }

    function updatePercentage(percentage: number) {
        if (!Number.isFinite(percentage)) {
            nSamplesToSelect.set(null);
            userEnteredPercentage.set(null);
            return;
        }
        const total = get(filteredSampleCount);
        const result = total > 0 ? Math.round((percentage / 100) * total) : 0;
        nSamplesToSelect.set(result);
        // Lock the display to what the user typed so that background
        // filteredSampleCount changes don't overwrite their entry.
        userEnteredPercentage.set(percentage);
    }

    const noSamples = derived(filteredSampleCount, ($count) => $count === 0);

    const notEnoughSamples = derived(
        [filteredSampleCount, nSamplesToSelect],
        ([$count, $n]) => $count > 0 && $n !== null && $n > $count
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
            $n !== null &&
            $n > 0 &&
            $name.trim().length > 0
    );

    const createButtonTooltip = derived(
        [instances, nSamplesToSelect, selectionResultTagName],
        ([$instances, $n, $name]) => {
            if ($instances.length === 0) return 'Add at least 1 strategy to create a selection.';
            if (!$instances.every(isStrategyInstanceValid))
                return 'Complete the required fields in all strategies.';
            if ($n === null || $n <= 0) return 'Enter a number of samples greater than 0.';
            if ($name.trim().length === 0) return 'Enter a tag name.';
            return '';
        }
    );

    function resetForm() {
        onSubmitSuccess();
        nSamplesToSelect.set(10);
        userEnteredPercentage.set(null); // let percentage re-derive from count
        selectionResultTagName.set('');
    }

    async function submitSelection() {
        const success = await submit({
            collectionId: getCollectionId(),
            isVideoCollection: getIsVideoCollection(),
            instances: get(instances),
            nSamplesToSelect: get(nSamplesToSelect) ?? 0,
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
        percentageToSelect,
        updateAbsolute,
        updatePercentage,
        selectionResultTagName,
        filteredSampleCount,
        noSamples,
        notEnoughSamples,
        sampleCountLabel,
        isFormValid,
        createButtonTooltip,
        isSubmitting,
        loadingMessage,
        handleFormSubmit
    };
}
