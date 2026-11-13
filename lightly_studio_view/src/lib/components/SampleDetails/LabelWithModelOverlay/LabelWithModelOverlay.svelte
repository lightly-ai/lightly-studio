<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import InstanceDeleteButton from '$lib/components/SampleDetails/FindInstancesOverlay/InstanceDeleteButton/InstanceDeleteButton.svelte';
    import PreviewClassTag from './PreviewClassTag/PreviewClassTag.svelte';
    import type { useLabelWithModel } from './useLabelWithModel.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
        scale: number;
        saveAs: SaveAs;
        // Owned by the parent, so the pop-up reads the same results.
        labelWithModel: ReturnType<typeof useLabelWithModel>;
    }

    let { sample, scale, saveAs, labelWithModel }: Props = $props();

    // Captured before the panel's handler, so Escape clears the results before it closes the tool.
    const onKeyDown = (event: KeyboardEvent) => {
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        if (event.key !== 'Escape' || labelWithModel.predictions.length === 0) return;
        labelWithModel.clear();
        event.stopPropagation();
    };
</script>

<svelte:window onkeydowncapture={onKeyDown} />

{#each labelWithModel.predictions as preview (preview)}
    <AnnotationPreview {preview} image={sample} {saveAs} />
    <PreviewClassTag {preview} {scale} />
{/each}
{#each labelWithModel.predictions as preview, index (preview)}
    <InstanceDeleteButton
        bbox={preview.bbox}
        {index}
        {scale}
        disabled={labelWithModel.isSaving}
        onDelete={() => labelWithModel.removePrediction(preview)}
    />
{/each}
