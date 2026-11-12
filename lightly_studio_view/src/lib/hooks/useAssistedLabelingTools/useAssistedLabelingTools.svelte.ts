import { untrack } from 'svelte';
import { fromStore } from 'svelte/store';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext
} from '$lib/contexts/SampleDetailsToolbar.svelte';
import { useAssistedLabelingStatus } from '$lib/hooks/useAssistedLabelingStatus';
import { useLabelingModels } from '$lib/hooks/useLabelingModels';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useStickyClassName } from '$lib/hooks/useStickyClass/useStickyClassName.svelte';
import { useSmartSelect } from '$lib/components/SampleDetails/SmartSelectOverlay/useSmartSelect.svelte';
import { DEFAULT_MAX_INSTANCES } from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.helpers';
import { useFindInstances } from '$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte';
import { useLabelWithModel } from '$lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte';

const DEFAULT_MODEL_THRESHOLD = 0.5;

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
    instancesPrompt = $state('');
    maxInstances = $state(DEFAULT_MAX_INSTANCES);
    isDrawingInstancesBox = $state(false);
    // Null selects the first model of the server.
    modelId = $state<string | null>(null);
    modelThreshold = $state(DEFAULT_MODEL_THRESHOLD);
}

// Shares the tool state between the pop-ups and the overlays, and falls back to the cursor
// tool when edit mode ends or assisted labeling becomes unusable.
export const useAssistedLabelingTools = (getParams: () => UseAssistedLabelingToolsParams) => {
    const assistedLabelingStatus = useAssistedLabelingStatus();
    const labelingModels = useLabelingModels(() => getParams().collectionId);
    const { context, setStatus } = useSampleDetailsToolbarContext();
    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const isEditingMode = fromStore(useGlobalStorage().isEditingMode);
    const state = new AssistedLabelingToolState();
    const stickyClass = useStickyClassName(() => getParams().collectionId);

    // A Space pan keeps the tool it interrupts active, so its prompts survive the pan.
    const tool = $derived(context.status === 'drag' ? context.panFrom : context.status);
    const activeTool = $derived(tool && isAssistedLabelingStatus(tool) ? tool : null);
    const isPanning = $derived(context.status === 'drag' && activeTool !== null);
    // Smart select uses drags for its boxes, find instances only while drawing a box.
    const blocksPan = $derived(
        context.status === 'smart-select' ||
            (context.status === 'find-instances' && state.isDrawingInstancesBox)
    );
    // A class picked in the tool's pop-up wins, else new annotations get the sticky class.
    const smartSelectClass = $derived(state.smartSelectClass ?? stickyClass.current ?? null);
    const instancesClass = $derived(state.instancesClass ?? stickyClass.current ?? null);
    const selectedModel = $derived(
        labelingModels.models.find((model) => model.id === state.modelId) ??
            labelingModels.models[0] ??
            null
    );
    // Object detection models return no masks.
    const modelSaveAs = $derived(
        selectedModel?.task === 'instance_segmentation' ? state.saveAs : 'box'
    );
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
            onSaved: () => {
                clearInstances();
                refetch();
            }
        };
    });

    const labelWithModel = useLabelWithModel(() => {
        const { collectionId, sampleId, refetch } = getParams();
        return {
            collectionId,
            sampleId,
            modelId: selectedModel?.id ?? null,
            threshold: state.modelThreshold,
            saveAs: modelSaveAs,
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
        endInstancesBoxDrawing();
    };

    $effect(() => {
        const status = context.status;
        if (!isAssistedLabelingStatus(status)) return;
        // The model tool uses its own server, the other tools use fal.ai.
        const disabledReason =
            status === 'label-with-model'
                ? labelingModels.disabledReason
                : assistedLabelingStatus.disabledReason;
        if (!isEditingMode.current || disabledReason !== null) setStatus('cursor');
    });

    // Leaving a tool, e.g. by a tool switch or Escape, ends box drawing and drops its prompts.
    // Untracked, so the state the clears read, e.g. isSaving, does not rerun this.
    $effect(() => {
        const tool = activeTool;
        untrack(() => {
            if (tool !== 'smart-select') smartSelect.clear();
            if (tool !== 'find-instances') clearInstances();
            if (tool !== 'label-with-model') labelWithModel.clear();
        });
    });

    return {
        state,
        smartSelect,
        instances,
        labelWithModel,
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
        },
        get labelingModels() {
            return labelingModels.models;
        },
        get selectedModel() {
            return selectedModel;
        },
        get modelSaveAs() {
            return modelSaveAs;
        }
    };
};
