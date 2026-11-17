<script lang="ts">
    import Check from '@lucide/svelte/icons/check';
    import { Button } from '$lib/components/ui/button';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';
    import type {
        ModelSuggestion,
        useModelSuggestionReview
    } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';

    interface Props {
        collectionId: string;
        suggestion: ModelSuggestion;
        index: number;
        review: ReturnType<typeof useModelSuggestionReview>;
        disabled: boolean;
    }
    let { collectionId, suggestion, index, review, disabled }: Props = $props();
</script>

<li class="rounded p-1">
    <div class="flex flex-wrap items-center gap-1">
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
        {#if suggestion.status === 'pending'}
            <Button
                size="sm"
                variant="outline"
                {disabled}
                aria-label={`Accept suggestion ${index + 1}`}
                onclick={() => review.accept(suggestion.id)}>Accept</Button
            >
            <Button
                size="sm"
                variant="outline"
                {disabled}
                aria-label={`Reject suggestion ${index + 1}`}
                onclick={() => review.reject(suggestion.id)}>Reject</Button
            >
        {:else}
            {#if suggestion.status === 'accepted'}
                <span class="inline-flex items-center gap-1 text-xs text-blue-400"
                    ><Check class="size-3" /> Accepted</span
                >
            {:else}
                <span class="text-xs text-muted-foreground">Rejected</span>
            {/if}
            <Button
                size="sm"
                variant="ghost"
                {disabled}
                aria-label={`Undo decision for suggestion ${index + 1}`}
                onclick={() => review.undo(suggestion.id)}>Undo</Button
            >
        {/if}
    </div>
    {#if review.focusedId === suggestion.id && !disabled}
        {#if suggestion.status === 'accepted' && review.hideAccepted}
            <Button size="sm" variant="ghost" onclick={() => review.setHideAccepted(false)}
                >Show on image</Button
            >
        {/if}
        <div class="space-y-1 pt-1">
            <p class="text-xs text-muted-foreground">Annotation class</p>
            <AnnotationClassSelect
                {collectionId}
                value={suggestion.preview.class_name}
                onChange={review.changeClass}
                label="Annotation class"
            />
        </div>
    {/if}
</li>
