<script lang="ts">
    import { getModelSuggestionAppearance } from '../modelSuggestionAppearance';
    import ResizableRectangle from '$lib/components/ResizableRectangle/ResizableRectangle.svelte';
    import type {
        ModelSuggestion,
        useModelSuggestionReview
    } from '../useModelSuggestionReview.svelte';

    interface Props {
        suggestion: ModelSuggestion;
        review: ReturnType<typeof useModelSuggestionReview>;
        sample: { width: number; height: number };
        scale: number;
    }

    let { suggestion, review, sample, scale }: Props = $props();
    // The shared rectangle mutates its box during a drag. Keep those changes local until clamped.
    let box = $state({ x: 0, y: 0, width: 1, height: 1 });
    $effect(() => {
        box = { ...suggestion.box };
    });
    const updateBox = (next: ModelSuggestion['box']) =>
        review.updateBox(suggestion.id, next, sample);
</script>

<ResizableRectangle
    bbox={box}
    {scale}
    colorStroke={getModelSuggestionAppearance(suggestion.status).colorStroke}
    onResize={updateBox}
    onMove={updateBox}
/>
