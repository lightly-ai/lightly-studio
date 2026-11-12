<script lang="ts">
    import { ChevronDown, ChevronRight, X } from '@lucide/svelte';
    import { Button as IconButton } from '$lib/components/ui/button';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { highlightRange, splitMatch } from '$lib/components/FilterList/filterList.helpers';
    import { getFieldSearchContext } from './fieldSearchContext';

    interface Props {
        /** Field name as stored, e.g. `split` or `Width`. */
        title: string;
        /** Short state text after the title, e.g. "Updating…". */
        status?: string;
        /** Whether the field body shows. Only used with `onToggleExpanded`. */
        expanded?: boolean;
        /** Makes the title a button that shows or hides the field body. */
        onToggleExpanded?: () => void;
        /** Shows a remove button that takes the field out of the filters. */
        onRemove?: () => void;
        /** Shows a checkbox before the title. `true` when the field has an active filter. */
        checked?: boolean;
        /** Short value of the active filter. Shows only when `checked` and collapsed. */
        summary?: string;
        /** Called when the checkbox is unchecked. */
        onClear?: () => void;
    }

    const {
        title,
        status,
        expanded = true,
        onToggleExpanded,
        onRemove,
        checked,
        summary,
        onClear
    }: Props = $props();

    const getSearch = getFieldSearchContext();
    const [before, match, after] = $derived(splitMatch(title, highlightRange(title, getSearch())));

    function handleCheckedChange(next: boolean | 'indeterminate') {
        if (next === true) {
            if (!expanded) onToggleExpanded?.();
            return;
        }
        onClear?.();
    }
</script>

<div class="flex min-h-6 items-center justify-between gap-2">
    {#if checked !== undefined}
        <Checkbox
            bind:checked={() => checked === true, () => {}}
            onCheckedChange={handleCheckedChange}
            aria-label={`${title} filter`}
        />
    {/if}
    <h3 class="min-w-0 flex-1 truncate text-sm font-medium" {title}>
        {#if onToggleExpanded}
            <button
                type="button"
                class="flex w-full min-w-0 items-center gap-1 text-left"
                aria-expanded={expanded}
                onclick={onToggleExpanded}
            >
                {#if expanded}
                    <ChevronDown class="size-4 shrink-0" />
                {:else}
                    <ChevronRight class="size-4 shrink-0" />
                {/if}
                <span class="truncate"
                    >{before}{#if match}<mark class="rounded-sm bg-primary/25 text-foreground"
                            >{match}</mark
                        >{/if}{after}</span
                >
            </button>
        {:else}
            {title}
        {/if}
    </h3>
    <div class="flex shrink-0 items-center gap-1">
        {#if status}
            <span class="text-xs text-muted-foreground" role="status">{status}</span>
        {/if}
        {#if checked && summary && !expanded}
            <span class="max-w-32 truncate text-xs text-muted-foreground" title={summary}>
                {summary}
            </span>
        {/if}
        {#if onRemove}
            <IconButton
                variant="ghost"
                size="icon"
                class="size-6"
                aria-label={`Remove metadata field ${title}`}
                onclick={onRemove}
            >
                <X class="size-4" />
            </IconButton>
        {/if}
    </div>
</div>
