<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { Box, SquareDashed } from '@lucide/svelte';
    import type { LabelingModelView } from '$lib/api/lightly_studio_local';
    import { Select } from '$lib/components/Select';
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { useLabelWithModel } from '$lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte';
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
    const predictionCount = $derived(labelWithModel.predictions.length);
</script>

<AnnotationToolPopUp
    title="Label with model"
    {collectionId}
    {saveAs}
    {onSaveAsChange}
    showSaveControls={predictionCount > 0}
    showSaveAs={model?.task === 'instance_segmentation'}
    saveLabel={`Save ${predictionCount}`}
    canSave={labelWithModel.canSave}
    isSaving={labelWithModel.isSaving}
    onSave={() => void labelWithModel.save()}
    onClear={labelWithModel.clear}
>
    <Select
        {items}
        value={model?.id}
        size="sm"
        placeholder="Select a model"
        testId="label-with-model-select"
        onValueChange={onModelChange}
    />
    <ThresholdInput value={threshold} onChange={onThresholdChange} />
    <ModelRunControls
        {predictionCount}
        isGenerating={labelWithModel.isGenerating}
        isEmptyResult={labelWithModel.isEmptyResult}
        canGenerate={labelWithModel.canGenerate}
        onRun={() => void labelWithModel.generate()}
    />
</AnnotationToolPopUp>
