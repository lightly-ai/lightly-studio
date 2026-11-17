<script lang="ts">
    import { Button } from '$lib/components/ui/button';
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
    {review.acceptedSuggestions.length} accepted · {review.pendingCount} pending · {review
        .suggestions.length -
        review.acceptedSuggestions.length -
        review.pendingCount} rejected
</p>
<div class="flex gap-2">
    <Button variant="ghost" size="sm" {disabled} onclick={review.acceptAll}>Accept all</Button>
    <Button variant="ghost" size="sm" {disabled} onclick={review.rejectAll}>Reject all</Button>
</div>
<ul class="max-h-48 overflow-y-auto" aria-label="Annotation suggestions">
    {#each review.suggestions as suggestion, index (suggestion.id)}
        <li class="flex flex-wrap items-center gap-1 rounded p-1">
            <Button
                variant={review.focusedId === suggestion.id ? 'secondary' : 'ghost'}
                class="min-w-24 flex-1 justify-between gap-2 px-1"
                {disabled}
                aria-pressed={review.focusedId === suggestion.id}
                onclick={() => review.focus(suggestion.id)}
            >
                <span class="truncate">{index + 1}. {suggestion.preview.class_name}</span>
                <span>{Math.round(suggestion.preview.score * 100)}%</span>
            </Button>
            <Button
                size="sm"
                variant={suggestion.status === 'accepted' ? 'default' : 'outline'}
                {disabled}
                aria-label={`Accept suggestion ${index + 1}`}
                aria-pressed={suggestion.status === 'accepted'}
                onclick={() => review.accept(suggestion.id)}>Accept</Button
            >
            <Button
                size="sm"
                variant={suggestion.status === 'rejected' ? 'destructive' : 'outline'}
                {disabled}
                aria-label={`Reject suggestion ${index + 1}`}
                aria-pressed={suggestion.status === 'rejected'}
                onclick={() => review.reject(suggestion.id)}>Reject</Button
            >
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
