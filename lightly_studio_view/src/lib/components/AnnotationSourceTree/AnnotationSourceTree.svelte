<script lang="ts">
    import { Settings } from '@lucide/svelte';
    import { get } from 'svelte/store';
    import type { AnnotationCountMode, ImageFilter } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import FilterListRow from '$lib/components/FilterList/FilterListRow.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { resolveEffectiveColorBySource } from '$lib/utils';
    import AnnotationClassRows from './AnnotationClassRows.svelte';
    import AnnotationSourceNode from './AnnotationSourceNode.svelte';
    import { buildSourceTree, formatCount } from './buildSourceTree';
    import { useSourceLabelCounts } from './useSourceLabelCounts.svelte';

    interface Props {
        /** The collection on screen. Its pairs and its annotation sources are used. */
        collectionId: string;
        /** The image collection the counts are taken on. */
        countsCollectionId: string;
        /** The other filters of the grid. The counts follow them. */
        countsFilter?: ImageFilter;
        countMode: AnnotationCountMode;
        /** Show only this source, e.g. on the annotations grid of one source. */
        singleSourceId?: string;
        showVisibilityToggle?: boolean;
        /** The "No annotations" row, pinned at the bottom. Omit to hide it. */
        unannotatedRow?: {
            current_count: number;
            total_count: number;
            selected: boolean;
            onToggle: () => void;
        };
    }

    let {
        collectionId,
        countsCollectionId,
        countsFilter,
        countMode,
        singleSourceId,
        showVisibilityToggle = false,
        unannotatedRow
    }: Props = $props();

    const sourcesQuery = useAnnotationCollections(() => ({
        collectionId: singleSourceId ? undefined : collectionId
    }));
    const countsQuery = useSourceLabelCounts(() => ({
        collectionId: countsCollectionId,
        filter: countsFilter,
        countMode
    }));
    const { pairs, togglePair, setSource } = $derived(useAnnotationPairFilter(collectionId));
    const { selectedCollectionIds, setSelectedCollectionIds, multipleSourcesVisible } =
        useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();
    const { openSettingsDialog } = useSettingsDialog();

    const sources = $derived(
        singleSourceId
            ? [{ id: singleSourceId, name: '' }]
            : (sourcesQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );
    const tree = $derived(buildSourceTree(sources, countsQuery.data ?? [], $pairs));
    const colorBySource = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

    const toggleSourceVisibility = (sourceId: string) => {
        const ids = get(selectedCollectionIds);
        setSelectedCollectionIds(
            ids.includes(sourceId) ? ids.filter((id) => id !== sourceId) : [...ids, sourceId]
        );
    };
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
        {#if tree.length > 1}
            {#each tree as node (node.id)}
                <AnnotationSourceNode
                    {node}
                    isHidden={!$selectedCollectionIds.includes(node.id)}
                    showSourceColor={colorBySource}
                    showClassColor={!colorBySource}
                    {showVisibilityToggle}
                    onToggleSource={(checked) => setSource(node.id, node.labelIds, checked)}
                    onTogglePair={(labelId) => togglePair(node.id, labelId)}
                    onToggleVisibility={() => toggleSourceVisibility(node.id)}
                />
            {/each}
        {:else if tree.length === 1 && tree[0].classes.length > 0}
            <AnnotationClassRows
                items={tree[0].classes}
                showClassColor={!colorBySource}
                {showVisibilityToggle}
                onToggle={(labelId) => togglePair(tree[0].id, labelId)}
            />
        {:else}
            <p class="text-sm text-diffuse-foreground">No annotations yet.</p>
        {/if}
        {#if unannotatedRow}
            <FilterListRow
                item={{
                    id: 'no-annotations',
                    label: 'No annotations',
                    selected: unannotatedRow.selected,
                    count: formatCount(unannotatedRow.current_count, unannotatedRow.total_count)
                }}
                checked={unannotatedRow.selected}
                onToggle={unannotatedRow.onToggle}
                testId="annotation-source-tree-pinned"
                emphasized
            />
        {/if}
    </div>
</Segment>
