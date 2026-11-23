<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import { PreviewDeleteButton } from '$lib/components/SampleDetails/PreviewDeleteButton';
    import PreviewClassTag from './PreviewClassTag/PreviewClassTag.svelte';
    import type { useLabelWithModel } from './useLabelWithModel.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number };
        scale: number;
        saveAs: SaveAs;
        // Owned by the parent, so the pop-up reads the same results.
        labelWithModel: ReturnType<typeof useLabelWithModel>;
    }

    let { sample, scale, saveAs, labelWithModel }: Props = $props();

    // Captured before the panel's handler, so Escape clears the results before it closes the tool.
    // During a save, Escape closes the tool; the save ends and the unsaved results go.
    const onKeyDown = (event: KeyboardEvent) => {
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        const canClear = labelWithModel.predictions.length > 0 && !labelWithModel.isSaving;
        if (event.key !== 'Escape' || !canClear) return;
        labelWithModel.clear();
        event.stopPropagation();
    };
</script>

<svelte:window onkeydowncapture={onKeyDown} />

{#each labelWithModel.predictions as preview (preview)}
    <AnnotationPreview {preview} image={sample} {saveAs} />
{/each}
<!-- After all previews, so that no mask covers a tag or a button. -->
{#each labelWithModel.predictions as preview, index (preview)}
    <PreviewClassTag {preview} {scale} />
    <PreviewDeleteButton
        bbox={preview.bbox}
        label="Delete suggested annotation"
        {index}
        {scale}
        disabled={labelWithModel.isSaving}
        onDelete={() => labelWithModel.removePrediction(preview)}
    />
{/each}
