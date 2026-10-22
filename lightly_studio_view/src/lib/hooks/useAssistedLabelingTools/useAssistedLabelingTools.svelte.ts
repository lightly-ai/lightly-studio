import { fromStore } from 'svelte/store';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext
} from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const noop = () => undefined;
const idleSmartSelect = {
    canSave: false,
    isPending: false,
    needsPositivePoint: false,
    save: noop,
    clear: noop
};

// A class, so child components can update the fields without mutating a $state prop.
class AssistedLabelingToolState {
    saveAs = $state<'mask' | 'box'>('mask');
    smartSelectClass = $state<string | null>(null);
    smartSelect = $state<{
        canSave: boolean;
        isPending: boolean;
        needsPositivePoint: boolean;
        save: () => void;
        clear: () => void;
    }>(idleSmartSelect);
}

// Shares the tool state between the pop-up and the overlay, and falls back to the cursor
// tool when edit mode ends or assisted labeling becomes unusable.
export const useAssistedLabelingTools = () => {
    const assistedLabelingStatus = useAssistedLabelingStatus();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const isEditingMode = fromStore(useGlobalStorage().isEditingMode);
    const state = new AssistedLabelingToolState();

    // A Space pan keeps the tool it interrupts active, so its prompts survive the pan.
    const tool = $derived(context.status === 'drag' ? context.panFrom : context.status);
    const activeTool = $derived(tool && isAssistedLabelingStatus(tool) ? tool : null);
    const isPanning = $derived(context.status === 'drag' && activeTool !== null);
    const smartSelectClass = $derived(
        state.smartSelectClass ?? annotationLabelContext.annotationLabel
    );

    $effect(() => {
        if (
            isAssistedLabelingStatus(context.status) &&
            (!isEditingMode.current || assistedLabelingStatus.disabledReason !== null)
        )
            setStatus('cursor');
    });

    // Leaving the tool drops the actions of its unmounted overlay.
    $effect(() => {
        if (activeTool !== 'smart-select') state.smartSelect = idleSmartSelect;
    });

    return {
        state,
        get activeTool() {
            return activeTool;
        },
        get isPanning() {
            return isPanning;
        },
        get smartSelectClass() {
            return smartSelectClass;
        }
    };
};
