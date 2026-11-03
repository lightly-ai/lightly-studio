<script lang="ts">
    import ClassDot from './ClassDot.svelte';
    import SourceIcon from './SourceIcon.svelte';
    import TreeChildRow from './TreeChildRow.svelte';
    import { formatCount, type PairRow } from './pairRows';
    import type { MatchRange } from './treeSearch';

    interface Props {
        rows: PairRow[];
        /** What each row names: its class (under a source) or its source (under a class). */
        show: 'class' | 'source';
        find?: (text: string) => MatchRange | null;
        onToggle: (row: PairRow) => void;
        onOnly: (row: PairRow) => void;
    }

    let { rows, show, find, onToggle, onOnly }: Props = $props();
</script>

{#each rows as row (`${row.sourceId}:${row.labelId}`)}
    {@const label = show === 'class' ? row.className : row.sourceName}
    {#snippet leading()}
        {#if show === 'class'}
            <ClassDot className={row.className} />
        {:else}
            <SourceIcon sourceName={row.sourceName} />
        {/if}
    {/snippet}
    <TreeChildRow
        {label}
        ariaLabel={row.sourceName ? `${row.className} in ${row.sourceName}` : row.className}
        checked={row.ticked}
        count={formatCount(row.current, row.total)}
        range={find?.(label) ?? null}
        {leading}
        testId="annotation-class"
        onToggle={() => onToggle(row)}
        onOnly={() => onOnly(row)}
    />
{/each}
