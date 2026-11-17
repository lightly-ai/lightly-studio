<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { LabelingModelView } from '$lib/api/lightly_studio_local';
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { useLabelWithModel } from '$lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte';
    import ModelSuggestionList from './ModelSuggestionList/ModelSuggestionList.svelte';
    import ModelRunSettings from './ModelRunSettings/ModelRunSettings.svelte';
    import ModelRunControls from './ModelRunControls/ModelRunControls.svelte';

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

    const isBusy = $derived(labelWithModel.isSaving || labelWithModel.isGenerating);
    const acceptedCount = $derived(labelWithModel.review.acceptedSuggestions.length);
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
    saveLabel={`Save ${acceptedCount} accepted`}
    canSave={labelWithModel.canSave}
    isSaving={labelWithModel.isSaving}
    onSave={() => void labelWithModel.save()}
    onClear={labelWithModel.clear}
>
    <ModelRunSettings
        {models}
        {model}
        {threshold}
        {onThresholdChange}
        disabled={isBusy}
        onModelChange={(value) => {
            if (value === model?.id) return;
            labelWithModel.requestChange(() => {
                labelWithModel.clear();
                onModelChange(value);
            });
        }}
    />
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
        <p class="text-xs text-muted-foreground">
            {saveAs === 'box'
                ? 'Select a suggestion to move or resize its box.'
                : 'To resize a box, choose Box under Save as.'}
        </p>
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
