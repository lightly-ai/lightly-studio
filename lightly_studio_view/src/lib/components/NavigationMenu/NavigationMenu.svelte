<script lang="ts">
    import type { BreadcrumbLevel } from './types';
    import { findNavigationPath, buildBreadcrumbLevels } from './utils';
    import { page } from '$app/state';
    import { LayoutDashboard } from '@lucide/svelte';
    import { type CollectionView } from '$lib/api/lightly_studio_local';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { routeHelpers } from '$lib/routes';
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

    const breadcrumbLevels: BreadcrumbLevel[] = $derived.by(() => {
        if (!currentCollectionId) {
            return [
                {
                    selected: {
                        title: collection.group_component_name || collection.name || 'Dataset',
                        id: `dataset-${collection.collection_id}`,
                        href: routeHelpers.toCollectionHome(
                            datasetId,
                            collection.sample_type.toLowerCase(),
                            collection.collection_id
                        ),
                        isSelected: false,
                        icon: LayoutDashboard
                    },
                    siblings: []
                }
            ];
        }

        return buildBreadcrumbLevels(navigationPath, collection, currentCollectionId, datasetId);
    });

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
