<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useSettings } from '$lib/hooks/useSettings';
    import CollapseAllButton from './CollapseAllButton.svelte';
    import ColorBySwitch from './ColorBySwitch.svelte';
    import GroupBySwitch from './GroupBySwitch.svelte';
    import TreeChildRow from './TreeChildRow.svelte';
    import TreeGroupRow from './TreeGroupRow.svelte';
    import TreeRootRow from './TreeRootRow.svelte';
    import TreeSearchField from './TreeSearchField.svelte';
    import { groupPairRows } from './groupPairRows';
    import { buildPairRows, formatCount, summarizeRows } from './pairRows';
    import { createTreeActions } from './treeActions';
    import { buildMatcher, filterGroups, rowsInScope } from './treeSearch';
    import {
        buildTreeBranches,
        buildUnannotatedRows,
        pairLeaf,
        tickState,
        toPairKey
    } from './treeBranches';
    import {
        useAnnotationPairCounts,
        useUnannotatedImageCounts
    } from './useAnnotationPairCounts.svelte';

    interface Props {
        collectionId: string;
        /** A flat class list without groups and "No annotations", for one annotation source. */
        flat?: boolean;
    }

    let { collectionId, flat = false }: Props = $props();

    const { imageFilter } = useImageFilters();
    const { annotationColorModeStore, setAnnotationColorMode } = useSettings();
    const sourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const pairsQuery = useAnnotationPairCounts(() => ({ collectionId, filter: $imageFilter }));
    const unannotatedQuery = useUnannotatedImageCounts(() => ({
        collectionId,
        filter: $imageFilter,
        enabled: !flat
    }));
    const tree = $derived(useAnnotationTreeState(collectionId));
    const { untickedPairs, untickedUnannotated, hiddenPairs, groupBy, openGroups } = $derived(tree);

    const sources = $derived(
        (sourcesQuery.data ?? []).map((source) => ({ id: source.collection_id, name: source.name }))
    );
    const rows = $derived(
        buildPairRows(sources, pairsQuery.data ?? [], $untickedPairs, $hiddenPairs)
    );
    const unannotated = $derived(
        buildUnannotatedRows(sources, unannotatedQuery.data ?? [], $untickedUnannotated)
    );
    const groups = $derived(groupPairRows(rows, $groupBy, sources));

    // The search is local to this component and is not saved.
    let query = $state('');
    let useRegex = $state(false);
    const matcher = $derived(buildMatcher(query, useRegex));
    const find = $derived(matcher?.find ?? null);
    const shownGroups = $derived(find ? filterGroups(groups, find, $groupBy) : groups);
    const shownRows = $derived(find ? rows.filter((row) => find(row.className)) : rows);
    // "No annotations" rows match no search, so a search hides them.
    const shownUnannotated = $derived(find ? [] : unannotated);
    const branches = $derived(
        flat ? [] : buildTreeBranches(shownGroups, $groupBy, shownUnannotated)
    );
    const flatLeaves = $derived(
        flat ? shownRows.map((row) => pairLeaf(row, row.className, 'class')) : []
    );
    const allLeaves = $derived([...flatLeaves, ...branches.flatMap((branch) => branch.leaves)]);
    const total = $derived(summarizeRows(rows));
    // The root eye acts on the rows in scope, which a search narrows.
    const eyeRows = $derived(flat ? shownRows : rowsInScope(shownGroups));
    const setAllVisible = (visible: boolean) => tree.setVisible(eyeRows.map(toPairKey), visible);

    const actions = createTreeActions(
        () => tree,
        () => ({ allPairs: rows.map(toPairKey), sourceIds: flat ? [] : sources.map((s) => s.id) })
    );

    // More than 3 groups start collapsed until the user opens them. A search opens its matches
    // without changing the stored choice.
    const isOpen = (id: string) => !!find || ($openGroups[id] ?? branches.length <= 3);
    const anyOpen = $derived(branches.some((branch) => isOpen(branch.id)));
    const setAllOpen = (open: boolean) => {
        for (const branch of branches) {
            if (isOpen(branch.id) !== open) tree.toggleOpen(branch.id, !open);
        }
    };
</script>

<Segment title="Annotations">
    <div class="space-y-1" data-testid="annotation-tree">
        <div class="mb-2">
            <ColorBySwitch value={$annotationColorModeStore} onChange={setAnnotationColorMode} />
        </div>
        {#if !flat}
            <div class="mb-2 flex items-center gap-1">
                <div class="min-w-0 flex-1">
                    <GroupBySwitch value={$groupBy} onChange={tree.setGroupBy} />
                </div>
                {#if !find}
                    <CollapseAllButton {anyOpen} onToggle={setAllOpen} />
                {/if}
            </div>
        {/if}
        <TreeSearchField
            bind:query
            bind:useRegex
            invalid={matcher?.invalid ?? false}
            placeholder={flat ? 'Search classes…' : 'Search sources and classes…'}
        />
        <TreeRootRow
            tick={tickState(allLeaves)}
            eye={eyeRows.length > 0 ? summarizeRows(eyeRows).eye : undefined}
            count={rows.length > 0 ? formatCount(total.current, total.total) : undefined}
            onToggle={(ticked) => actions.setTicked(allLeaves, ticked)}
            onToggleEye={setAllVisible}
        />
        <div class="space-y-1 pl-4">
            {#each flatLeaves as leaf (leaf.id)}
                <TreeChildRow
                    {leaf}
                    colorMode={$annotationColorModeStore}
                    {find}
                    onToggle={() => actions.setTicked([leaf], !leaf.ticked)}
                    onOnly={() => actions.only([leaf])}
                    onToggleEye={(visible) => actions.setVisible([leaf], visible)}
                />
            {/each}
            {#each branches as branch (`${$groupBy}:${branch.id}`)}
                <TreeGroupRow
                    {branch}
                    colorMode={$annotationColorModeStore}
                    {find}
                    open={isOpen(branch.id)}
                    onToggleOpen={() => tree.toggleOpen(branch.id, isOpen(branch.id))}
                    onSetTicked={actions.setTicked}
                    onOnly={actions.only}
                    onSetVisible={actions.setVisible}
                />
            {/each}
        </div>
    </div>
</Segment>
