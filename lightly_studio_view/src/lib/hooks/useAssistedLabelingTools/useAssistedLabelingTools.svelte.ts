import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext
} from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';
import type { SaveAs } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';

const noop = () => undefined;

// A class, so child components can update the fields without mutating a $state prop.
class AssistedLabelingToolState {
    saveAs = $state<SaveAs>('mask');
    smartSelectClass = $state<string | null>(null);
    smartSelect = $state<{ canSave: boolean; save: () => void; clear: () => void }>({
        canSave: false,
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

    const activeTool = $derived(isAssistedLabelingStatus(context.status) ? context.status : null);
    const smartSelectClass = $derived(
        state.smartSelectClass ?? annotationLabelContext.annotationLabel
    );

    $effect(() => {
        if (activeTool && assistedLabelingStatus.disabledReason !== null) setStatus('cursor');
    });

    return {
        state,
        get activeTool() {
            return activeTool;
        },
        get smartSelectClass() {
            return smartSelectClass;
        }
    };
};
