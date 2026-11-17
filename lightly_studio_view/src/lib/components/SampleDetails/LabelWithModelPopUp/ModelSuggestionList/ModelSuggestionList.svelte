<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import type { useModelSuggestionReview } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';
    import ModelSuggestionRow from './ModelSuggestionRow.svelte';

    interface Props {
        collectionId: string;
        review: ReturnType<typeof useModelSuggestionReview>;
        disabled: boolean;
    }
    let { collectionId, review, disabled }: Props = $props();
</script>

<div class="text-xs" aria-live="polite">
    <p>
        {review.acceptedSuggestions.length} accepted · {review.pendingCount} pending · {review
            .suggestions.length -
            review.acceptedSuggestions.length -
            review.pendingCount} rejected
    </p>
    {#if review.pendingCount === 0}
        <p class="mt-1 font-medium">
            {review.acceptedSuggestions.length
                ? `Review complete · ${review.acceptedSuggestions.length} accepted`
                : 'All suggestions rejected.'}
        </p>
    {/if}
</div>
<label class="flex items-center gap-2 py-1 text-xs">
    <Checkbox
        checked={review.hideAccepted}
        {disabled}
        onCheckedChange={(value) => review.setHideAccepted(value === true)}
    />
    Hide accepted on image
</label>
<div class="flex gap-2">
    <Button variant="ghost" size="sm" {disabled} onclick={review.acceptAll}>Accept all</Button>
    <Button variant="ghost" size="sm" {disabled} onclick={review.rejectAll}>Reject all</Button>
</div>
<ul class="max-h-48 overflow-y-auto" aria-label="Annotation suggestions">
    {#each review.suggestions as suggestion, index (suggestion.id)}
        <ModelSuggestionRow {collectionId} {suggestion} {index} {review} {disabled} />
    {/each}
</ul>
