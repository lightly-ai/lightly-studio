<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';
    import { cn } from '$lib/utils';
    import type {
        ModelSuggestion,
        useModelSuggestionReview
    } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';
    import ModelSuggestionActions from './ModelSuggestionActions.svelte';

    interface Props {
        collectionId: string;
        suggestion: ModelSuggestion;
        review: ReturnType<typeof useModelSuggestionReview>;
        disabled: boolean;
    }
    let { collectionId, suggestion, review, disabled }: Props = $props();
    const classLabelId = $props.id();
    let row = $state<HTMLLIElement>();
    const isSelected = $derived(review.focusedId === suggestion.id);
    $effect(() => {
        if (!isSelected || !row?.parentElement) return;
        const list = row.parentElement;
        const rowBounds = row.getBoundingClientRect();
        const listBounds = list.getBoundingClientRect();
        if (rowBounds.top < listBounds.top) list.scrollTop += rowBounds.top - listBounds.top;
        else if (rowBounds.bottom > listBounds.bottom)
            list.scrollTop += rowBounds.bottom - listBounds.bottom;
    });
</script>

<li
    bind:this={row}
    class={cn('rounded border border-transparent p-1', isSelected && 'border-white/60 bg-white/10')}
    aria-current={isSelected ? 'true' : undefined}
    onfocusin={() => {
        if (!disabled) review.focus(suggestion.id);
    }}
>
    <div class="flex items-center gap-1">
        <div class="min-w-0 flex-1">
            <span id={classLabelId} class="sr-only">Annotation class</span>
            <AnnotationClassSelect
                labelledBy={classLabelId}
                {collectionId}
                value={suggestion.preview.class_name}
                {disabled}
                className="h-8 px-1 text-sm"
                onChange={(className) => review.changeClass(suggestion.id, className)}
            />
        </div>
        <span class="shrink-0 text-xs tabular-nums"
            >{Math.round(suggestion.preview.score * 100)}%</span
        >
        <ModelSuggestionActions {suggestion} {review} {disabled} />
    </div>
    {#if isSelected && suggestion.status === 'accepted' && review.hideAccepted}
        <Button size="sm" variant="ghost" {disabled} onclick={() => review.setHideAccepted(false)}
            >Show on image</Button
        >
    {/if}
</li>
