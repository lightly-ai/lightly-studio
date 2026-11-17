<script lang="ts">
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import PreviewClassTag from '../PreviewClassTag/PreviewClassTag.svelte';
    import { getSuggestionPreview, type ModelSuggestion } from '../useModelSuggestionReview.svelte';
    import { getModelSuggestionAppearance } from '../modelSuggestionAppearance';
    interface Props {
        suggestion: ModelSuggestion;
        sample: { width: number };
        scale: number;
        saveAs: 'box' | 'mask';
        isSelected: boolean;
        disabled: boolean;
        onSelect: () => void;
    }
    let { suggestion, sample, scale, saveAs, isSelected, disabled, onSelect }: Props = $props();
    const preview = $derived(getSuggestionPreview(suggestion, saveAs));
    const appearance = $derived(getModelSuggestionAppearance(suggestion.status));
</script>

<g>
    {#if isSelected}
        <rect
            x={preview.bbox.x}
            y={preview.bbox.y}
            width={preview.bbox.width}
            height={preview.bbox.height}
            fill="rgba(255, 255, 255, 0.08)"
            stroke="white"
            stroke-width="6"
            vector-effect="non-scaling-stroke"
            pointer-events="none"
            data-testid="suggestion-highlight"
        />
    {/if}
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
        stroke={isSelected ? appearance.colorStroke : 'transparent'}
        stroke-width="3"
        vector-effect="non-scaling-stroke"
        role="button"
        tabindex={disabled ? -1 : 0}
        aria-label={`Review suggestion: ${suggestion.preview.class_name}`}
        aria-pressed={isSelected}
        onpointerdown={(event) => event.stopPropagation()}
        onclick={(event) => {
            event.stopPropagation();
            if (!disabled) onSelect();
        }}
        onkeydown={(event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            event.stopPropagation();
            if (!disabled) onSelect();
        }}
    />
</g>
