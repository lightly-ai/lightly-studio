<script lang="ts">
    import { Loader2, Play, RotateCw } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        predictionCount: number;
        isGenerating: boolean;
        isEmptyResult: boolean;
        canGenerate: boolean;
        onRun: () => void;
    }

    let { predictionCount, isGenerating, isEmptyResult, canGenerate, onRun }: Props = $props();

    const annotationsLabel = $derived(
        predictionCount === 1 ? 'suggested annotation' : 'suggested annotations'
    );
</script>

{#if predictionCount > 0}
    <div class="flex items-center justify-between gap-2">
        <span class="text-xs font-medium">{predictionCount} {annotationsLabel}</span>
        <Button
            variant="ghost"
            size="sm"
            class="-mr-1 h-7 shrink-0 gap-1 px-2 text-xs text-muted-foreground"
            disabled={!canGenerate}
            onclick={onRun}
        >
            {#if isGenerating}
                <Loader2 class="size-3.5 animate-spin" />
            {:else}
                <RotateCw class="size-3.5" />
            {/if}
            Run again
        </Button>
    </div>
    <p class="text-xs text-muted-foreground">Delete the wrong ones, then save.</p>
{:else}
    <Button class="h-8 gap-1.5" disabled={!canGenerate} onclick={onRun}>
        {#if isGenerating}
            <Loader2 class="size-4 animate-spin" />
            Running…
        {:else}
            <Play class="size-4" />
            Run model
        {/if}
    </Button>
    {#if isEmptyResult}
        <p class="text-xs text-muted-foreground">
            The model suggested no annotations. Lower the confidence or pick another model.
        </p>
    {/if}
{/if}
