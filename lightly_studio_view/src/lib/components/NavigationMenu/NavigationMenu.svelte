<script lang="ts">
    import type { BreadcrumbLevel, NavigationMenuItem } from './types';
    import { findNavigationPath, buildBreadcrumbLevels } from './utils';
    import { page } from '$app/state';
    import { LayoutDashboard, LayoutGrid } from '@lucide/svelte';
    import { EvaluationTaskType, type CollectionView } from '$lib/api/lightly_studio_local';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { routeHelpers } from '$lib/routes';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    const {
        collection
    }: {
        collection: CollectionView;
    } = $props();

    const { setCollection } = useGlobalStorage();

    $effect(() => {
        // update the collections hashmap
        function addCollectionRecursive(collection: CollectionView) {
            setCollection(collection);

            collection.children?.map((child) => {
                addCollectionRecursive(child);
            });
        }

        addCollectionRecursive(collection);
    });

    // Get datasetId from URL params (always available in routes where NavigationMenu is used)
    const datasetId = $derived(page.params.dataset_id!);

    const currentCollectionId = $derived(page.params.collection_id);

    const navigationPath = $derived(
        currentCollectionId ? findNavigationPath(collection, currentCollectionId) : null
    );

    // Object-detection runs are the only ones with per-box (TP/FP/FN) matches.
    const evaluationRunsQuery = useEvaluationRuns(() => ({ datasetId: collection.dataset_id }));
    const evaluationMatchItems: NavigationMenuItem[] = $derived(
        (evaluationRunsQuery.data ?? [])
            .filter((run) => run.task_type === EvaluationTaskType.OBJECT_DETECTION)
            .map((run) => ({
                title: `Matches: ${run.name}`,
                id: `evaluation-matches-${run.id}`,
                icon: LayoutGrid,
                href: routeHelpers.toEvaluationMatches({
                    datasetId,
                    collectionType: page.params.collection_type!,
                    collectionId: page.params.collection_id!,
                    evaluationRunId: run.id
                }),
                isSelected: page.params.evaluation_run_id === run.id
            }))
    );

    const breadcrumbLevels: BreadcrumbLevel[] = $derived(
        buildBreadcrumbLevels(
            navigationPath,
            collection,
            currentCollectionId,
            datasetId,
            evaluationMatchItems
        )
    );

    const { user } = useAuth();
</script>

<div class="flex gap-2" data-testid="navigation-menu">
    {#if user}
        <MenuItem
            item={{
                title: 'Datasets',
                id: 'datasets',
                href: '/workspace/datasets',
                isSelected: false,
                icon: LayoutDashboard
            }}
        />
    {/if}

    {#each breadcrumbLevels as level (level.selected.id)}
        <MenuItem
            item={level.selected}
            siblings={level.siblings.length > 1 ? level.siblings : []}
        />
    {/each}
</div>
