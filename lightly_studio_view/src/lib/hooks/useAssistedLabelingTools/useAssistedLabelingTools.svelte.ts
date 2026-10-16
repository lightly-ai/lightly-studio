import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
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
// tool if the provider becomes unusable.
export const useAssistedLabelingTools = () => {
    const provider = useAssistedLabelingProvider();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const state = new AssistedLabelingToolState();

    const activeTool = $derived(context.status === 'smart-select' ? context.status : null);

    $effect(() => {
        if (activeTool && provider.tools.smartSelectDisabledReason !== null) setStatus('cursor');
    });

    return {
        state,
        get activeTool() {
            return activeTool;
        },
        get tools() {
            return provider.tools;
        }
    };
};
