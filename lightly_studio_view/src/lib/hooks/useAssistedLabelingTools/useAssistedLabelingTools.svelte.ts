import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
import type { SaveAs } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';

const noop = (): void => undefined;

// A class, so child components can update the fields without mutating a $state prop.
class AssistedLabelingToolState {
    saveAs = $state<SaveAs>('mask');
    smartSelectClass = $state<string | null>(null);
    smartSelect = $state<{ canSave: boolean; save: () => void; clear: () => void }>({
        canSave: false,
        save: noop,
        clear: noop
    });
    instancesClass = $state<string | null>(null);
    instancesPrompt = $state('');
    maxInstances = $state<number | null>(null);
    isDrawingInstancesBox = $state(false);
    instances = $state({
        boxCount: 0,
        isGenerating: false,
        resultCount: 0,
        canSave: false,
        generate: noop,
        save: noop,
        clear: noop
    });
}

// Shares the tool state between the pop-ups and the overlays, and falls back to the cursor
// tool if the provider becomes unusable for the active tool.
export const useAssistedLabelingTools = () => {
    const provider = useAssistedLabelingProvider();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const state = new AssistedLabelingToolState();

    const activeTool = $derived(
        context.status === 'smart-select' || context.status === 'find-instances'
            ? context.status
            : null
    );
    const selectedMaxInstances = $derived(
        Math.min(
            state.maxInstances ?? provider.tools.defaultMaxInstances,
            provider.tools.maxInstances
        )
    );

    $effect(() => {
        if (!activeTool) return;
        const { smartSelectDisabledReason, instancesDisabledReason } = provider.tools;
        const disabledReason =
            activeTool === 'smart-select' ? smartSelectDisabledReason : instancesDisabledReason;
        if (disabledReason !== null) setStatus('cursor');
    });

    // Leaving the tool, e.g. by a tool switch or Escape, ends box drawing.
    $effect(() => {
        if (activeTool !== 'find-instances') state.isDrawingInstancesBox = false;
    });

    return {
        state,
        get activeTool() {
            return activeTool;
        },
        get selectedMaxInstances() {
            return selectedMaxInstances;
        },
        get tools() {
            return provider.tools;
        }
    };
};
