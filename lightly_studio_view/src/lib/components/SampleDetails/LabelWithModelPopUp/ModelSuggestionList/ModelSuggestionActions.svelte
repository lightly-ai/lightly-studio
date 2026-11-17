<script lang="ts">
    import Check from '@lucide/svelte/icons/check';
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components/ui/button';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import type {
        ModelSuggestion,
        useModelSuggestionReview
    } from '$lib/components/SampleDetails/LabelWithModelOverlay/useModelSuggestionReview.svelte';
    interface Props {
        suggestion: ModelSuggestion;
        review: ReturnType<typeof useModelSuggestionReview>;
        disabled: boolean;
    }
    let { suggestion, review, disabled }: Props = $props();
</script>

{#if suggestion.status === 'pending'}
    <Tooltip content="Accept suggestion" noTriggerRole>
        <Button
            size="icon"
            variant="outline"
            class="size-8"
            {disabled}
            aria-label={`Accept suggestion: ${suggestion.preview.class_name}`}
            onclick={() => review.accept(suggestion.id)}><Check class="size-4" /></Button
        >
    </Tooltip>
    <Tooltip content="Reject suggestion" noTriggerRole>
        <Button
            size="icon"
            variant="outline"
            class="size-8"
            {disabled}
            aria-label={`Reject suggestion: ${suggestion.preview.class_name}`}
            onclick={() => review.reject(suggestion.id)}><X class="size-4" /></Button
        >
    </Tooltip>
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
        class="h-8 px-1"
        {disabled}
        aria-label={`Undo decision: ${suggestion.preview.class_name}`}
        onclick={() => review.undo(suggestion.id)}>Undo</Button
    >
{/if}
