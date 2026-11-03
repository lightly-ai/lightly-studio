<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { cn } from '$lib/utils';

    // Variant "radio" of the annotation source picker: one radio per source group. Same props
    // as AnnotationTargetButton, so the two can be swapped.
    interface Props {
        sourceName: string;
        /** Whether new annotations are written to this source. */
        isTarget: boolean;
        /** Whether the source is hidden. A hidden source can't take new annotations. */
        isSourceHidden: boolean;
        /** Whether no source is picked yet, so every radio asks for a click. */
        needsPick: boolean;
        onSetTarget: () => void;
    }

    let { sourceName, isTarget, isSourceHidden, needsPick, onSetTarget }: Props = $props();

    const label = $derived(
        isSourceHidden
            ? `Show ${sourceName} to add new annotations to it`
            : isTarget
              ? `New annotations go to ${sourceName}`
              : `Add new annotations to ${sourceName}`
    );
</script>

<Tooltip content={label}>
    <button
        type="button"
        role="radio"
        aria-label={label}
        aria-checked={isTarget}
        aria-disabled={isSourceHidden}
        class={cn(
            'flex size-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
            isSourceHidden && 'cursor-not-allowed border-dashed border-muted-foreground/40',
            !isSourceHidden && isTarget && 'border-primary',
            !isSourceHidden && !isTarget && needsPick && 'border-amber-400 hover:bg-amber-400/15',
            !isSourceHidden &&
                !isTarget &&
                !needsPick &&
                'border-muted-foreground hover:border-foreground'
        )}
        onclick={(e) => {
            e.stopPropagation();
            // aria-disabled instead of disabled, so the tooltip still says why.
            if (!isSourceHidden) onSetTarget();
        }}
        data-testid={`annotation-target-radio-${sourceName}`}
    >
        {#if isTarget}
            <span class="size-1.5 rounded-full bg-primary"></span>
        {/if}
    </button>
</Tooltip>
