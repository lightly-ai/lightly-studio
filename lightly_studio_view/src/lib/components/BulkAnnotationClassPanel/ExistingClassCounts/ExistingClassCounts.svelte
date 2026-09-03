<script lang="ts">
    import Spinner from '$lib/components/Spinner/Spinner.svelte';

    interface Props {
        /** Annotation source the counts were taken from. */
        source: string;
        /** Classification annotations the selected images already have, per annotation class. */
        counts: { className: string; sampleCount: number }[];
        isLoading: boolean;
    }

    const { source, counts, isLoading }: Props = $props();
</script>

<div class="space-y-1.5" data-testid="existing-class-counts">
    <p class="text-xs font-medium text-muted-foreground">
        Annotation classes already in {source}
    </p>
    {#if isLoading}
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner size="small" />
            <span data-testid="existing-class-counts-loading">Loading annotation classes…</span>
        </div>
    {:else if counts.length === 0}
        <p class="text-xs text-muted-foreground" data-testid="existing-class-counts-empty">
            The selected images have no annotations in this annotation source.
        </p>
    {:else}
        <ul class="max-h-32 space-y-0.5 overflow-y-auto text-xs">
            {#each counts as { className, sampleCount } (className)}
                <li class="flex items-center justify-between gap-2">
                    <span class="min-w-0 truncate">{className}</span>
                    <span class="shrink-0 tabular-nums text-muted-foreground">{sampleCount}</span>
                </li>
            {/each}
        </ul>
    {/if}
</div>
