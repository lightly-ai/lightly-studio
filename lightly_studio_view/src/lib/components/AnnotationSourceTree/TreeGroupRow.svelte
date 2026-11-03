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
    const collapsedSummary = $derived(
        summary.ticked === group.rows.length ? 'all' : `${summary.ticked} of ${group.rows.length}`
    );
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
            <ChevronRight class="size-4 transition-transform {expanded ? 'rotate-90' : ''}" />
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
                'min-w-0 flex-1 truncate text-base font-medium',
                summary.state === 'unchecked' && 'text-muted-foreground'
            )}
            ><HighlightedText
                text={group.name}
                range={find?.(group.name) ?? null}
            />{#if !expanded && !isEmpty}<span
                    class="ml-1.5 text-xs font-normal text-muted-foreground"
                    data-testid="annotation-group-summary">{collapsedSummary}</span
                >{/if}</span
        >
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
        {#if summary.count}
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
