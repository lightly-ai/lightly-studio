<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import TreeChildRow from './TreeChildRow.svelte';
    import TreeGroupRow from './TreeGroupRow.svelte';
    import TreeRootRow from './TreeRootRow.svelte';
    import { groupPairRows } from './groupPairRows';
    import { buildPairRows, formatCount, summarizeRows } from './pairRows';
    import { createTreeActions } from './treeActions';
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
    const branches = $derived(
        flat ? [] : buildTreeBranches(groupPairRows(rows, $groupBy, sources), $groupBy, unannotated)
    );
    const flatLeaves = $derived(flat ? rows.map((row) => pairLeaf(row, row.className)) : []);
    const allLeaves = $derived([...flatLeaves, ...branches.flatMap((branch) => branch.leaves)]);
    const total = $derived(summarizeRows(rows));

    const actions = createTreeActions(
        () => tree,
        () => ({ allPairs: rows.map(toPairKey), sourceIds: flat ? [] : sources.map((s) => s.id) })
    );

    const isOpen = (id: string) => $openGroups[id] ?? true;
</script>

<Segment title="Annotations">
    <div class="space-y-1" data-testid="annotation-tree">
        <TreeRootRow
            tick={tickState(allLeaves)}
            count={rows.length > 0 ? formatCount(total.current, total.total) : undefined}
            onToggle={(ticked) => actions.setTicked(allLeaves, ticked)}
        />
        <div class="space-y-1 pl-4">
            {#each flatLeaves as leaf (leaf.id)}
                <TreeChildRow
                    {leaf}
                    onToggle={() => actions.setTicked([leaf], !leaf.ticked)}
                    onOnly={() => actions.only([leaf])}
                />
            {/each}
            {#each branches as branch (`${$groupBy}:${branch.id}`)}
                <TreeGroupRow
                    {branch}
                    open={isOpen(branch.id)}
                    onToggleOpen={() => tree.toggleOpen(branch.id, isOpen(branch.id))}
                    onSetTicked={actions.setTicked}
                    onOnly={actions.only}
                />
            {/each}
        </div>
    </div>
</Segment>
