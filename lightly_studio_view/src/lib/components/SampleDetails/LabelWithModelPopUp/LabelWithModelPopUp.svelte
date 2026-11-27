<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { LabelingModelView } from '$lib/api/lightly_studio_local';
    import { Select } from '$lib/components/Select';
    import { useBrowserModels } from '$lib/hooks';
    import {
        AnnotationToolPopUp,
        SaveAsToggle,
        SaveButtons
    } from '$lib/components/SampleDetails/AnnotationToolPopUp';
    import type { useLabelWithModel } from '$lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte';
    import ModelRunControls from './ModelRunControls/ModelRunControls.svelte';
    import ThresholdInput from './ThresholdInput/ThresholdInput.svelte';
    import { toModelKey } from '$lib/hooks/useAssistedLabelingTools/toModelKey';
    import { LOAD_MODEL_FILE_VALUE, toModelSelectItems } from './modelSelectItems';

    type SaveAs = ComponentProps<typeof SaveAsToggle>['saveAs'];
    type AutoLabelModel = LabelingModelView & { runsIn: 'browser' | 'server' };

    interface Props {
        models: AutoLabelModel[];
        model: AutoLabelModel | null;
        // Receives the toModelKey of the picked model.
        onModelChange: (modelKey: string) => void;
        threshold: number;
        onThresholdChange: (value: number) => void;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        // Owned by the parent, so the overlay reads the same results.
        labelWithModel: ReturnType<typeof useLabelWithModel>;
    }

    let {
        models,
        model,
        onModelChange,
        threshold,
        onThresholdChange,
        saveAs,
        onSaveAsChange,
        labelWithModel
    }: Props = $props();

    const { loadProgress, addModelFile } = useBrowserModels();
    let fileInput: HTMLInputElement;

    const items = $derived(toModelSelectItems(models));
    const predictionCount = $derived(labelWithModel.predictions.length);
    // Only the selected model's first run downloads anything.
    const downloadProgress = $derived($loadProgress?.modelId === model?.id ? $loadProgress : null);

    const selectModel = (value: string) => {
        if (value === LOAD_MODEL_FILE_VALUE) fileInput.click();
        else onModelChange(value);
    };

    const loadModelFile = async () => {
        const file = fileInput.files?.[0];
        fileInput.value = '';
        if (file) onModelChange(toModelKey({ id: await addModelFile(file), runsIn: 'browser' }));
    };
</script>

{#snippet saveControls()}
    {#if model?.task === 'instance_segmentation'}
        <SaveAsToggle {saveAs} {onSaveAsChange} />
    {/if}
    <SaveButtons
        saveLabel={`Save ${predictionCount}`}
        canSave={labelWithModel.canSave}
        isSaving={labelWithModel.isSaving}
        onSave={() => void labelWithModel.save()}
        onClear={labelWithModel.clear}
    />
{/snippet}

<AnnotationToolPopUp
    title="Auto-label"
    saveControls={predictionCount > 0 ? saveControls : undefined}
>
    <Select
        {items}
        value={model ? toModelKey(model) : undefined}
        size="sm"
        placeholder="Select a model"
        testId="label-with-model-select"
        disabled={labelWithModel.isSaving}
        onValueChange={selectModel}
    />
    <input
        bind:this={fileInput}
        type="file"
        accept=".onnx"
        class="hidden"
        data-testid="load-model-file-input"
        onchange={() => void loadModelFile()}
    />
    <ThresholdInput value={threshold} onChange={onThresholdChange} />
    <ModelRunControls
        {predictionCount}
        isGenerating={labelWithModel.isGenerating}
        isEmptyResult={labelWithModel.isEmptyResult}
        canGenerate={labelWithModel.canGenerate}
        {downloadProgress}
        onRun={() => void labelWithModel.generate()}
    />
</AnnotationToolPopUp>
