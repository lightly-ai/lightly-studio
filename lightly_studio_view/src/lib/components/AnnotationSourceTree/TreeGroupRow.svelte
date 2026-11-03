<script lang="ts">
    import { ChevronRight } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { cn } from '$lib/utils/shadcn';
    import ClassDot from './ClassDot.svelte';
    import HighlightedText from './HighlightedText.svelte';
    import PairRows from './PairRows.svelte';
    import RowAction from './RowAction.svelte';
    import SourceIcon from './SourceIcon.svelte';
    import type { TreeGroup } from './groupPairRows';
    import { summarizeRows, type PairRow } from './pairRows';
    import type { MatchRange } from './treeSearch';

    interface Props {
        group: TreeGroup;
        open: boolean;
        find?: (text: string) => MatchRange | null;
        onToggleOpen: () => void;
        onSetRows: (rows: PairRow[], ticked: boolean) => void;
        onOnlyRows: (rows: PairRow[]) => void;
    }

    let { group, open, find, onToggleOpen, onSetRows, onOnlyRows }: Props = $props();

    const summary = $derived(summarizeRows(group.rows));
    const isEmpty = $derived(group.rows.length === 0);
    const expanded = $derived(open && !isEmpty);
    const isSource = $derived(group.sourceId !== undefined);
    // A class group sums the same images over its sources, so it counts sources instead.
    const sourcesSummary = $derived(
        summary.state === 'partial'
            ? `${summary.ticked} of ${group.rows.length} sources`
            : `${group.rows.length} ${group.rows.length === 1 ? 'source' : 'sources'}`
    );
    // The checkbox already says "all" or "none"; a partial collapsed source spells it out.
    const showCollapsedSummary = $derived(isSource && !expanded && summary.state === 'partial');
</script>

<div class="mb-1" data-testid="annotation-source-node">
    <div
        class="group flex w-full items-center gap-2 rounded-md bg-muted px-2 py-1.5"
        data-testid="annotation-source-row"
    >
        <button
            type="button"
            aria-label="{expanded ? 'Collapse' : 'Expand'} {group.name}"
            aria-expanded={expanded}
            disabled={isEmpty}
            class="flex shrink-0 items-center disabled:opacity-30"
            onclick={onToggleOpen}
        >
            <span class={cn('flex transition-transform', expanded && 'rotate-90')}>
                <ChevronRight class="size-4" />
            </span>
        </button>
        <Checkbox
            checked={summary.state === 'checked'}
            indeterminate={summary.state === 'partial'}
            aria-label={group.name}
            disabled={isEmpty}
            onCheckedChange={() => onSetRows(group.rows, summary.state !== 'checked')}
        />
        <span class={cn('flex shrink-0', summary.state === 'unchecked' && 'opacity-40')}>
            {#if isSource}
                <SourceIcon sourceName={group.name} />
            {:else}
                <ClassDot className={group.name} />
            {/if}
        </span>
        <span
            class={cn(
                'min-w-0 truncate text-sm font-medium',
                summary.state === 'unchecked' && 'text-muted-foreground'
            )}
            title={group.name}
            ><HighlightedText text={group.name} range={find?.(group.name) ?? null} /></span
        >
        <!-- The summary gives way first, then the name: name > count > summary. -->
        {#if showCollapsedSummary}
            <span
                class="min-w-0 shrink-[1000] truncate text-xs text-muted-foreground"
                data-testid="annotation-group-summary">{summary.ticked}/{group.rows.length}</span
            >
        {/if}
        <span class="flex-1"></span>
        {#if !isEmpty}
            {#if summary.state !== 'checked'}
                <RowAction
                    label="All"
                    ariaLabel="Show all of {group.name}"
                    onclick={() => onSetRows(group.rows, true)}
                />
            {/if}
            <RowAction
                label="Only"
                ariaLabel="Show only {group.name}"
                onclick={() => onOnlyRows(group.rows)}
            />
        {/if}
        {#if !isSource && !isEmpty}
            <span
                class="shrink-0 whitespace-nowrap text-xs text-muted-foreground"
                data-testid="annotation-source-count">{sourcesSummary}</span
            >
        {:else if summary.count}
            <span
                class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground"
                data-testid="annotation-source-count">{summary.count}</span
            >
        {/if}
    </div>
    {#if expanded}
        <div class="ml-4 mt-1 space-y-1 border-l border-foreground/30 pl-3 pr-2">
            <PairRows
                rows={group.rows}
                show={isSource ? 'class' : 'source'}
                {find}
                onToggle={(row) => onSetRows([row], !row.ticked)}
                onOnly={(row) => onOnlyRows([row])}
            />
        </div>
    {/if}
</div>
