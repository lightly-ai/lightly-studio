import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext,
    type AssistedLabelingStatus
} from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';

const noop = () => undefined;

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
    }>({
        canSave: false,
        isPending: false,
        needsPositivePoint: false,
        save: noop,
        clear: noop
    });
}

// Shares the tool state between the pop-up and the overlay, and falls back to the cursor
// tool if assisted labeling becomes unusable.
export const useAssistedLabelingTools = () => {
    const assistedLabelingStatus = useAssistedLabelingStatus();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const state = new AssistedLabelingToolState();

    // The last tool stays active while panning, so its prompts survive the pan.
    let lastTool = $state<AssistedLabelingStatus | null>(null);
    $effect(() => {
        if (context.status === 'drag') return;
        lastTool = isAssistedLabelingStatus(context.status) ? context.status : null;
    });
    const isPanning = $derived(context.status === 'drag' && lastTool !== null);
    const activeTool = $derived(
        isAssistedLabelingStatus(context.status) ? context.status : isPanning ? lastTool : null
    );
    const smartSelectClass = $derived(
        state.smartSelectClass ?? annotationLabelContext.annotationLabel
    );

    $effect(() => {
        if (
            isAssistedLabelingStatus(context.status) &&
            assistedLabelingStatus.disabledReason !== null
        )
            setStatus('cursor');
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
