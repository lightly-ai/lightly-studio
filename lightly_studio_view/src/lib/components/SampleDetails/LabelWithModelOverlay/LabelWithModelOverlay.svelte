<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import ModelSuggestionBox from './ModelSuggestionBox/ModelSuggestionBox.svelte';
    import ModelSuggestionPreview from './ModelSuggestionPreview/ModelSuggestionPreview.svelte';
    import type { useLabelWithModel } from './useLabelWithModel.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
        isPanning?: boolean;
        scale: number;
        saveAs: SaveAs;
        // Owned by the parent, so the pop-up reads the same results.
        labelWithModel: Pick<
            ReturnType<typeof useLabelWithModel>,
            'review' | 'isSaving' | 'isGenerating'
        >;
    }

    let { sample, scale, saveAs, labelWithModel, isPanning = false }: Props = $props();

    const suggestions = $derived([
        ...labelWithModel.review.suggestions.filter(
            (suggestion) => suggestion.id !== labelWithModel.review.focusedId
        ),
        ...labelWithModel.review.suggestions.filter(
            (suggestion) => suggestion.id === labelWithModel.review.focusedId
        )
    ]);

    // Escape clears focus first; a second Escape reaches the editor tool handler.
    const onKeyDown = (event: KeyboardEvent) => {
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        if (event.key !== 'Escape' || labelWithModel.review.focusedId === null) return;
        labelWithModel.review.focus(null);
        event.stopPropagation();
    };
</script>

<svelte:window onkeydowncapture={onKeyDown} />

{#each suggestions as suggestion (suggestion.id)}
    {#if labelWithModel.review.isVisible(suggestion)}
        <ModelSuggestionPreview
            {suggestion}
            {sample}
            {scale}
            {saveAs}
            isSelected={labelWithModel.review.focusedId === suggestion.id}
            disabled={labelWithModel.isSaving || labelWithModel.isGenerating || isPanning}
            onSelect={() => labelWithModel.review.focus(suggestion.id)}
        />
    {/if}
{/each}

{#if labelWithModel.review.focusedSuggestion && !labelWithModel.isSaving && !labelWithModel.isGenerating && !isPanning}
    {@const suggestion = labelWithModel.review.focusedSuggestion}
    {#if labelWithModel.review.isVisible(suggestion) && (saveAs === 'box' || !suggestion.preview.segmentation_mask)}
        <ModelSuggestionBox {suggestion} {sample} {scale} review={labelWithModel.review} />
    {/if}
{/if}
