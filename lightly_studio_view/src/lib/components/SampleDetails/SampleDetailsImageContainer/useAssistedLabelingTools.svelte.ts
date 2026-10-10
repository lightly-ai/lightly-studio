import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
import { usePrepareAnnotationImage } from '$lib/hooks/usePrepareAnnotationImage';

const noop = () => undefined;

// A class, so child components can update the fields without mutating a $state prop.
export class AssistedLabelingToolState {
    smartSelectClass = $state<string | null>(null);
    instancesClass = $state<string | null>(null);
    instancesPrompt = $state('');
    maxInstances = $state<number | null>(null);
    isDrawingInstancesBox = $state(false);
    smartSelect = $state<{ canSave: boolean; save: () => void; clear: () => void }>({
        canSave: false,
        save: noop,
        clear: noop
    });
    instances = $state<{
        boxCount: number;
        isGenerating: boolean;
        resultCount: number;
        generate: () => void;
        save: () => void;
        clear: () => void;
    }>({
        boxCount: 0,
        isGenerating: false,
        resultCount: 0,
        generate: noop,
        save: noop,
        clear: noop
    });
}

// Shares the state of the smart select and find all instances tools between their pop-ups
// and overlays. Prepares the image while a tool is active and falls back to the cursor tool
// if the provider becomes unusable.
export const useAssistedLabelingTools = (
    getParams: () => { collectionId: string; sampleId: string }
) => {
    const provider = useAssistedLabelingProvider();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const { prepareImage } = usePrepareAnnotationImage();
    const state = new AssistedLabelingToolState();

    const activeTool = $derived(
        context.status === 'wand' || context.status === 'instances' ? context.status : null
    );

    $effect(() => {
        if (!activeTool) return;
        const tools = provider.tools;
        const disabledReason =
            activeTool === 'wand' ? tools.smartSelectDisabledReason : tools.instancesDisabledReason;
        if (disabledReason !== null) {
            setStatus('cursor');
            return;
        }
        prepareImage(getParams());
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
