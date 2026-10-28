import { untrack } from 'svelte';
import { fromStore } from 'svelte/store';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext
} from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSmartSelect } from '$lib/components/SampleDetails/SmartSelectOverlay/useSmartSelect.svelte';
import { DEFAULT_MAX_INSTANCES } from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.helpers';
import { useFindInstances } from '$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte';

interface UseAssistedLabelingToolsParams {
    collectionId: string;
    sampleId: string;
    refetch: () => void;
}

// A class, so child components can update the fields without mutating a $state prop.
class AssistedLabelingToolState {
    saveAs = $state<'mask' | 'box'>('mask');
    smartSelectClass = $state<string | null>(null);
    instancesClass = $state<string | null>(null);
    // Kept across samples, so one prompt labels a whole series of images.
    instancesPrompt = $state('');
    maxInstances = $state(DEFAULT_MAX_INSTANCES);
    isDrawingInstancesBox = $state(false);
}

// Shares the tool state between the pop-ups and the overlays, and falls back to the cursor
// tool when edit mode ends or assisted labeling becomes unusable.
export const useAssistedLabelingTools = (getParams: () => UseAssistedLabelingToolsParams) => {
    const assistedLabelingStatus = useAssistedLabelingStatus();
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const isEditingMode = fromStore(useGlobalStorage().isEditingMode);
    const state = new AssistedLabelingToolState();

    // A Space pan keeps the tool it interrupts active, so its prompts survive the pan.
    const tool = $derived(context.status === 'drag' ? context.panFrom : context.status);
    const activeTool = $derived(tool && isAssistedLabelingStatus(tool) ? tool : null);
    const isPanning = $derived(context.status === 'drag' && activeTool !== null);
    // Smart select uses drags for its boxes, find instances only while drawing a box.
    const blocksPan = $derived(
        context.status === 'smart-select' ||
            (context.status === 'find-instances' && state.isDrawingInstancesBox)
    );
    const smartSelectClass = $derived(
        state.smartSelectClass ?? annotationLabelContext.annotationLabel
    );
    const instancesClass = $derived(state.instancesClass ?? annotationLabelContext.annotationLabel);
    const smartSelect = useSmartSelect(() => {
        const { collectionId, sampleId, refetch } = getParams();
        return {
            collectionId,
            sampleId,
            saveAs: state.saveAs,
            annotationClass: smartSelectClass,
            annotationSource: annotationLabelContext.annotationSource,
            onSaved: refetch
        };
    });
    const instances = useFindInstances(() => {
        const { collectionId, sampleId, refetch } = getParams();
        return {
            collectionId,
            sampleId,
            prompt: state.instancesPrompt,
            maxInstances: state.maxInstances,
            saveAs: state.saveAs,
            annotationClass: instancesClass,
            annotationSource: annotationLabelContext.annotationSource,
            onSaved: refetch
        };
    });

    const endInstancesBoxDrawing = () => {
        state.isDrawingInstancesBox = false;
    };

    const clearInstances = () => {
        instances.clear();
        state.instancesPrompt = '';
    };

    $effect(() => {
        if (
            isAssistedLabelingStatus(context.status) &&
            (!isEditingMode.current || assistedLabelingStatus.disabledReason !== null)
        )
            setStatus('cursor');
    });

    // Leaving a tool, e.g. by a tool switch or Escape, ends box drawing and drops its prompts.
    // Untracked, so the state the clears read, e.g. isSaving, does not rerun this.
    $effect(() => {
        const tool = activeTool;
        untrack(() => {
            if (tool !== 'smart-select') smartSelect.clear();
            if (tool !== 'find-instances') {
                endInstancesBoxDrawing();
                clearInstances();
            }
        });
    });

    return {
        state,
        smartSelect,
        instances,
        clearInstances,
        endInstancesBoxDrawing,
        get activeTool() {
            return activeTool;
        },
        get isPanning() {
            return isPanning;
        },
        get blocksPan() {
            return blocksPan;
        },
        get smartSelectClass() {
            return smartSelectClass;
        },
        get instancesClass() {
            return instancesClass;
        }
    };
};
