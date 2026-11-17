<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';
    import type { useModelSuggestionReview } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';

    interface Props {
        collectionId: string;
        review: ReturnType<typeof useModelSuggestionReview>;
        disabled: boolean;
    }

    let { collectionId, review, disabled }: Props = $props();
</script>

<p class="text-xs" aria-live="polite">
    {review.includedSuggestions.length} of {review.suggestions.length} suggestions selected
</p>
<div class="flex gap-2">
    <Button variant="ghost" size="sm" {disabled} onclick={review.selectAll}>Select all</Button>
    <Button variant="ghost" size="sm" {disabled} onclick={review.selectNone}>Select none</Button>
</div>
<ul class="max-h-48 overflow-y-auto" aria-label="Annotation suggestions">
    {#each review.suggestions as suggestion, index (suggestion.id)}
        <li class="flex items-center gap-2 rounded p-1">
            <Checkbox
                checked={suggestion.included}
                {disabled}
                aria-label={`Include suggestion ${index + 1}: ${suggestion.preview.class_name}`}
                onCheckedChange={(checked) => review.setIncluded(suggestion.id, checked === true)}
            />
            <Button
                variant={review.focusedId === suggestion.id ? 'secondary' : 'ghost'}
                class="min-w-0 flex-1 justify-between gap-2"
                {disabled}
                aria-pressed={review.focusedId === suggestion.id}
                onclick={() => review.focus(suggestion.id)}
            >
                <span class="truncate">{index + 1}. {suggestion.preview.class_name}</span>
                <span>{Math.round(suggestion.preview.score * 100)}%</span>
            </Button>
        </li>
    {/each}
</ul>
{#if review.focusedSuggestion && !disabled}
    <p class="text-xs text-muted-foreground">Annotation class</p>
    <AnnotationClassSelect
        {collectionId}
        value={review.focusedSuggestion.preview.class_name}
        onChange={review.changeClass}
        label="Annotation class"
    />
{/if}
