<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { cn } from '$lib/utils/shadcn';
    import HighlightedText from './HighlightedText.svelte';
    import RowAction from './RowAction.svelte';
    import type { MatchRange } from './treeSearch';

    interface Props {
        label: string;
        ariaLabel: string;
        checked: boolean;
        count?: string;
        range?: MatchRange | null;
        leading?: Snippet;
        testId: string;
        onToggle: () => void;
        onOnly: () => void;
    }

    let {
        label,
        ariaLabel,
        checked,
        count,
        range = null,
        leading,
        testId,
        onToggle,
        onOnly
    }: Props = $props();

    const rowId = $props.id();
</script>

<div class="group flex w-full items-center gap-2" title={label} data-testid="{testId}-item">
    <Checkbox id={rowId} {checked} aria-label={ariaLabel} onCheckedChange={onToggle} />
    <label for={rowId} class="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
        {#if leading}
            <span class={cn('flex shrink-0', !checked && 'opacity-40')}>{@render leading()}</span>
        {/if}
        <span
            class={cn('flex-1 truncate text-base', !checked && 'text-muted-foreground')}
            data-testid="{testId}-name"><HighlightedText text={label} {range} /></span
        >
    </label>
    <RowAction label="Only" ariaLabel="Show only {ariaLabel}" onclick={onOnly} />
    {#if count}
        <span class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground">{count}</span>
    {/if}
</div>
