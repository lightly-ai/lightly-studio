<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { splitMatch } from '$lib/components/AnnotationSourceTree/filterSourceTree';
    import { cn } from '$lib/utils/shadcn';
    import type { FilterListItem } from './filterList.helpers';

    interface Props {
        item: FilterListItem;
        checked: boolean;
        onToggle: () => void;
        testId: string;
        /** Mutes the label, for special rows such as "No annotations". */
        emphasized?: boolean;
        /** Highlights the first match of this text in the label. */
        highlight?: string;
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
        highlight = '',
        leading,
        trailing,
        trailingSpacer
    }: Props = $props();

    const rowId = $props.id();
    const parts = $derived(splitMatch(item.label, highlight));
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
            >{parts.before}{#if parts.match}<mark class="rounded-sm bg-primary/25 text-foreground"
                    >{parts.match}</mark
                >{/if}{parts.after}</span
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
