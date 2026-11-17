<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
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
    <g opacity={suggestion.included ? 1 : 0.35}>
        <AnnotationPreview preview={suggestion.preview} image={sample} {saveAs} />
        <PreviewClassTag preview={suggestion.preview} {scale} />
        <rect
            x={suggestion.preview.bbox.x}
            y={suggestion.preview.bbox.y}
            width={suggestion.preview.bbox.width}
            height={suggestion.preview.bbox.height}
            fill="transparent"
            stroke={labelWithModel.review.focusedId === suggestion.id ? '#ffffff' : 'transparent'}
            stroke-width="3"
            vector-effect="non-scaling-stroke"
            role="button"
            tabindex={labelWithModel.isSaving || labelWithModel.isGenerating ? -1 : 0}
            aria-label={`Review suggestion ${index + 1}: ${suggestion.preview.class_name}`}
            aria-pressed={labelWithModel.review.focusedId === suggestion.id}
            onpointerdown={(event) => event.stopPropagation()}
            onclick={(event) => {
                event.stopPropagation();
                if (!labelWithModel.isSaving && !labelWithModel.isGenerating)
                    labelWithModel.review.focus(suggestion.id);
            }}
            onkeydown={(event) => {
                if (event.key !== 'Enter' && event.key !== ' ') return;
                event.preventDefault();
                event.stopPropagation();
                if (!labelWithModel.isSaving && !labelWithModel.isGenerating)
                    labelWithModel.review.focus(suggestion.id);
            }}
        />
    </g>
{/each}
