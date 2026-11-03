<script lang="ts">
    import { Settings } from '@lucide/svelte';
    import type { AnnotationCountMode, ImageFilter } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import GroupBySwitch from './GroupBySwitch.svelte';
    import PairRows from './PairRows.svelte';
    import TreeChildRow from './TreeChildRow.svelte';
    import TreeGroupRow from './TreeGroupRow.svelte';
    import TreeSearchField from './TreeSearchField.svelte';
    import TreeStatusLine from './TreeStatusLine.svelte';
    import { groupPairRows } from './groupPairRows';
    import { buildPairRows, formatCount, toNamedPair } from './pairRows';
    import { createMatcher, matchRows } from './treeSearch';
    import { getTreeStatus } from './treeStatus';
    import { useSourceLabelCounts } from './useSourceLabelCounts.svelte';
    import { useTreeActions } from './useTreeActions';
    import { useTreeGroupBy } from './useTreeGroupBy';

    interface Props {
        /** The collection on screen. Its ticks and its annotation sources are used. */
        collectionId: string;
        /** The image collection the counts are taken on. */
        countsCollectionId: string;
        /** The other filters of the grid. The counts follow them. */
        countsFilter?: ImageFilter;
        countMode: AnnotationCountMode;
        /** Show only this source, e.g. on the annotations grid of one source. */
        singleSourceId?: string;
        /** The counts of the "No annotations" row, pinned at the bottom. Omit to hide it. */
        unannotatedCount?: { current_count: number; total_count: number };
    }

    let {
        collectionId,
        countsCollectionId,
        countsFilter,
        countMode,
        singleSourceId,
        unannotatedCount
    }: Props = $props();

    const sourcesQuery = useAnnotationCollections(() => ({
        collectionId: singleSourceId ? undefined : collectionId
    }));
    const countsQuery = useSourceLabelCounts(() => ({
        collectionId: countsCollectionId,
        filter: countsFilter,
        countMode
    }));
    const filter = $derived(useAnnotationPairFilter(collectionId));
    const { unticked, unannotatedTicked } = $derived(filter);
    const { groupBy, setGroupBy } = $derived(useTreeGroupBy(collectionId));
    const { openSettingsDialog } = useSettingsDialog();

    const sources = $derived(
        singleSourceId
            ? [{ id: singleSourceId, name: '' }]
            : (sourcesQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );
    const knownPairs = $derived(buildPairRows(sources, countsQuery.data ?? [], []));
    // The grid request needs every pair to send the ticked ones.
    $effect(() => {
        if (countsQuery.data) filter.setKnownPairs(knownPairs.map(toNamedPair));
    });

    let query = $state('');
    let useRegex = $state(false);
    const rows = $derived(buildPairRows(sources, countsQuery.data ?? [], $unticked));
    const matcher = $derived(createMatcher(query, useRegex));
    const searching = $derived(matcher.kind === 'ok');
    const matches = $derived(matchRows(rows, matcher));
    const find = $derived(matcher.kind === 'ok' ? matcher.find : undefined);
    const allGroups = $derived(groupPairRows(rows, $groupBy, sources));
    const groups = $derived(
        groupPairRows(matches, $groupBy, sources).filter((g) => !searching || g.rows.length > 0)
    );
    const status = $derived(
        getTreeStatus({
            rows,
            matches,
            searching,
            unannotatedTicked: unannotatedCount ? $unannotatedTicked : undefined
        })
    );
    const actions = useTreeActions({
        getFilter: () => filter,
        getRows: () => rows,
        getMatches: () => matches,
        hasUnannotatedRow: () => Boolean(unannotatedCount)
    });

    // More than 3 groups start collapsed. A search opens the matching ones without changing
    // what the user chose.
    let userOpen = $state<Record<string, boolean>>({});
    const isOpen = (id: string) =>
        searching || (userOpen[`${$groupBy}:${id}`] ?? allGroups.length <= 3);
    const toggleOpen = (id: string) => (userOpen[`${$groupBy}:${id}`] = !isOpen(id));
</script>

<Segment title="Annotations">
    {#snippet headerAction()}
        <Button
            variant="ghost"
            icon={Settings}
            ariaLabel="Manage annotation sources"
            buttonProps={{
                type: 'button',
                size: 'icon',
                class: 'size-7 text-muted-foreground',
                onclick: () => openSettingsDialog('annotation-sources')
            }}
        />
    {/snippet}
    <div class="space-y-2" data-testid="annotation-source-tree">
        <GroupBySwitch value={$groupBy} onChange={setGroupBy} />
        <TreeSearchField
            {query}
            {useRegex}
            invalid={matcher.kind === 'invalid'}
            onQueryChange={(value) => (query = value)}
            onRegexChange={(value) => (useRegex = value)}
        />
        <TreeStatusLine
            text={status.text}
            actions={status.actions}
            invalid={matcher.kind === 'invalid'}
            onAction={actions.runStatusAction}
        />
        {#if rows.length === 0 && sources.length <= 1}
            <p class="text-sm text-diffuse-foreground">No annotations yet.</p>
        {:else if sources.length <= 1}
            <div class="space-y-1">
                <PairRows
                    rows={matches}
                    show="class"
                    {find}
                    onToggle={(row) => actions.setRows([row], !row.ticked)}
                    onOnly={(row) => actions.onlyRows([row])}
                />
            </div>
        {:else}
            {#each groups as group (`${$groupBy}:${group.id}`)}
                <TreeGroupRow
                    {group}
                    open={isOpen(group.id)}
                    {find}
                    onToggleOpen={() => toggleOpen(group.id)}
                    onSetRows={actions.setRows}
                    onOnlyRows={actions.onlyRows}
                />
            {/each}
        {/if}
        {#if unannotatedCount && query.trim() === ''}
            <div class="mt-2 border-t pt-2 {sources.length > 1 ? 'pl-8 pr-2' : ''}">
                <TreeChildRow
                    label="No annotations"
                    ariaLabel="No annotations"
                    checked={$unannotatedTicked}
                    count={formatCount(
                        unannotatedCount.current_count,
                        unannotatedCount.total_count
                    )}
                    testId="annotation-source-tree-pinned"
                    onToggle={() => filter.setUnannotatedTicked(!$unannotatedTicked)}
                    onOnly={actions.onlyUnannotated}
                />
            </div>
        {/if}
    </div>
</Segment>
