<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import ModelSuggestionBox from './ModelSuggestionBox/ModelSuggestionBox.svelte';
    import { getSuggestionPreview } from './useModelSuggestionReview.svelte';
    import { getModelSuggestionAppearance } from './modelSuggestionAppearance';
    import PreviewClassTag from './PreviewClassTag/PreviewClassTag.svelte';
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

    // Escape clears focus first; a second Escape reaches the editor tool handler.
    const onKeyDown = (event: KeyboardEvent) => {
        if (isTextInputTarget(event.target) || isOverlayTarget(event.target)) return;
        if (event.key !== 'Escape' || labelWithModel.review.focusedId === null) return;
        labelWithModel.review.focus(null);
        event.stopPropagation();
    };
</script>

<svelte:window onkeydowncapture={onKeyDown} />

{#each labelWithModel.review.suggestions as suggestion, index (suggestion.id)}
    {@const preview = getSuggestionPreview(suggestion, saveAs)}
    {#if labelWithModel.review.isVisible(suggestion)}
        {@const appearance = getModelSuggestionAppearance(suggestion.status)}
        <g>
            <AnnotationPreview
                {preview}
                image={sample}
                {saveAs}
                colorStroke={appearance.colorStroke}
                colorFill={appearance.colorFill}
                strokeDasharray={appearance.strokeDasharray}
            />
            <PreviewClassTag {preview} {scale} color={appearance.tagColor} />
            <rect
                x={preview.bbox.x}
                y={preview.bbox.y}
                width={preview.bbox.width}
                height={preview.bbox.height}
                fill="transparent"
                stroke={labelWithModel.review.focusedId === suggestion.id
                    ? appearance.colorStroke
                    : 'transparent'}
                stroke-width="3"
                vector-effect="non-scaling-stroke"
                role="button"
                tabindex={labelWithModel.isSaving || labelWithModel.isGenerating || isPanning
                    ? -1
                    : 0}
                aria-label={`Review suggestion ${index + 1}: ${suggestion.preview.class_name}`}
                aria-pressed={labelWithModel.review.focusedId === suggestion.id}
                onpointerdown={(event) => event.stopPropagation()}
                onclick={(event) => {
                    event.stopPropagation();
                    if (!labelWithModel.isSaving && !labelWithModel.isGenerating && !isPanning)
                        labelWithModel.review.focus(suggestion.id);
                }}
                onkeydown={(event) => {
                    if (event.key !== 'Enter' && event.key !== ' ') return;
                    event.preventDefault();
                    event.stopPropagation();
                    if (!labelWithModel.isSaving && !labelWithModel.isGenerating && !isPanning)
                        labelWithModel.review.focus(suggestion.id);
                }}
            />
        </g>
    {/if}
{/each}

{#if labelWithModel.review.focusedSuggestion && !labelWithModel.isSaving && !labelWithModel.isGenerating && !isPanning}
    {@const suggestion = labelWithModel.review.focusedSuggestion}
    {#if labelWithModel.review.isVisible(suggestion) && (saveAs === 'box' || !suggestion.preview.segmentation_mask)}
        <ModelSuggestionBox {suggestion} {sample} {scale} review={labelWithModel.review} />
    {/if}
{/if}
