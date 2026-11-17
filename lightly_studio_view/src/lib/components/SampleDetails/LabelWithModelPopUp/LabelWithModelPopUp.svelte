<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import Box from '@lucide/svelte/icons/box';
    import SquareDashed from '@lucide/svelte/icons/square-dashed';
    import type { LabelingModelView } from '$lib/api/lightly_studio_local';
    import { Select } from '$lib/components/Select';
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { useLabelWithModel } from '$lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte';
    import ModelSuggestionList from './ModelSuggestionList/ModelSuggestionList.svelte';
    import ModelRunControls from './ModelRunControls/ModelRunControls.svelte';
    import ThresholdInput from './ThresholdInput/ThresholdInput.svelte';

    type SaveAs = ComponentProps<typeof AnnotationToolPopUp>['saveAs'];

    interface Props {
        collectionId: string;
        models: LabelingModelView[];
        model: LabelingModelView | null;
        onModelChange: (modelId: string) => void;
        threshold: number;
        onThresholdChange: (value: number) => void;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        // Owned by the parent, so the overlay reads the same results.
        labelWithModel: ReturnType<typeof useLabelWithModel>;
    }

    let {
        collectionId,
        models,
        model,
        onModelChange,
        threshold,
        onThresholdChange,
        saveAs,
        onSaveAsChange,
        labelWithModel
    }: Props = $props();

    const TASKS = {
        object_detection: { group: 'Object detection', icon: Box },
        instance_segmentation: { group: 'Instance segmentation', icon: SquareDashed }
    } as const;

    const items = $derived(
        models.map((item) => ({ value: item.id, label: item.id, ...TASKS[item.task] }))
    );
    const isBusy = $derived(labelWithModel.isSaving || labelWithModel.isGenerating);
    const selectedCount = $derived(labelWithModel.review.includedSuggestions.length);
    const predictionCount = $derived(labelWithModel.predictions.length);
</script>

<AnnotationToolPopUp
    title="Model-assisted labeling"
    panelWidth="360px"
    clearLabel="Discard suggestions"
    {collectionId}
    {saveAs}
    {onSaveAsChange}
    showSaveControls={predictionCount > 0}
    showSaveAs={model?.task === 'instance_segmentation'}
    saveLabel={`Save ${selectedCount} ${selectedCount === 1 ? 'annotation' : 'annotations'}`}
    canSave={labelWithModel.canSave}
    isSaving={labelWithModel.isSaving}
    onSave={() => void labelWithModel.save()}
    onClear={labelWithModel.clear}
>
    <fieldset disabled={isBusy} class="grid min-w-0 gap-1.5">
        <Select
            {items}
            disabled={isBusy}
            selectProps={{ 'aria-label': 'Model' }}
            value={model?.id}
            size="sm"
            placeholder="Select a model"
            testId="label-with-model-select"
            onValueChange={(value) => {
                if (value === model?.id) return;
                labelWithModel.requestChange(() => {
                    labelWithModel.clear();
                    onModelChange(value);
                });
            }}
        />
        {#if model}<p class="text-xs text-muted-foreground">{TASKS[model.task].group}</p>{/if}
        <ThresholdInput value={threshold} onChange={onThresholdChange} disabled={isBusy} />
    </fieldset>
    {#if labelWithModel.needsRegeneration}
        <p class="text-xs text-muted-foreground">
            Confidence changed. Generate suggestions again to apply it.
        </p>
    {/if}
    {#if labelWithModel.generationError}
        <p role="alert" class="text-xs text-destructive">{labelWithModel.generationError}</p>
    {/if}
    <ModelRunControls
        {predictionCount}
        isGenerating={labelWithModel.isGenerating}
        isEmptyResult={labelWithModel.isEmptyResult}
        canGenerate={labelWithModel.canGenerate}
        onRun={() => labelWithModel.requestChange(() => void labelWithModel.generate())}
    />
    {#if predictionCount > 0}
        <ModelSuggestionList {collectionId} review={labelWithModel.review} disabled={isBusy} />
        <p class="break-words text-xs text-muted-foreground">
            Annotation source: {labelWithModel.annotationSource}
        </p>
        {#if labelWithModel.annotationSourceBlockedReason}
            <p role="alert" class="text-xs text-destructive">
                {labelWithModel.annotationSourceBlockedReason}
            </p>
        {/if}
    {/if}
</AnnotationToolPopUp>
