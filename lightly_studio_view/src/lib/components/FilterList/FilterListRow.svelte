<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { cn } from '$lib/utils/shadcn';
    import { splitMatch, type FilterListItem } from './filterList.helpers';

    interface Props {
        item: FilterListItem;
        checked: boolean;
        onToggle: () => void;
        testId: string;
        /** Mutes the label, for special rows such as "No annotations". */
        emphasized?: boolean;
        /** Character range of the label to highlight. */
        highlight?: { start: number; end: number } | null;
        leading?: Snippet<[FilterListItem]>;
        trailing?: Snippet<[FilterListItem]>;
        /** Takes the trailing snippet's space without showing it, so counts line up. */
        trailingSpacer?: Snippet<[FilterListItem]>;
    }

    const {
        item,
        checked,
        onToggle,
        testId,
        emphasized = false,
        highlight = null,
        leading,
        trailing,
        trailingSpacer
    }: Props = $props();

    const rowId = $props.id();
    const [before, match, after] = $derived(splitMatch(item.label, highlight));
</script>

<div class="flex w-full items-center gap-2" title={item.label} data-testid="{testId}-item">
    <Checkbox
        id={rowId}
        {checked}
        aria-label={item.ariaLabel ?? item.label}
        onCheckedChange={onToggle}
    />
    <Label
        for={rowId}
        class="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    >
        {@render leading?.(item)}
        <span
            class={cn(
                'flex-1 truncate text-base font-normal',
                emphasized && 'text-muted-foreground'
            )}
            data-testid="{testId}-name"
            >{before}{#if match}<mark class="rounded-sm bg-primary/25 text-foreground">{match}</mark
                >{/if}{after}</span
        >
        {#if item.count !== undefined}
            <span class="text-sm font-normal text-diffuse-foreground" data-testid="{testId}-count"
                >{item.count}</span
            >
        {/if}
    </Label>
    {@render trailing?.(item)}
    {#if trailingSpacer}
        <div class="pointer-events-none invisible" aria-hidden="true">
            {@render trailingSpacer(item)}
        </div>
    {/if}
</div>
