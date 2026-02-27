<script lang="ts">
    import type { NavigationMenuItem, BreadcrumbLevel } from './types';
    import { findNavigationPath, buildBreadcrumbLevels, getMenuItem } from './utils';
    import { page } from '$app/state';
    import { LayoutDashboard } from '@lucide/svelte';
    import { type CollectionView } from '$lib/api/lightly_studio_local';
    import MenuItem from '../MenuItem/MenuItem.svelte';
    import { BreadcrumbSeparator } from '$lib/components/ui/breadcrumb';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    const {
        collection
    }: {
        collection: CollectionView;
    } = $props();

    const pageId = $derived(page.route.id);

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

    const breadcrumbLevels: BreadcrumbLevel[] = $derived(
        buildBreadcrumbLevels(navigationPath, collection, pageId, datasetId)
    );

    const { user } = useAuth();
</script>

<div class="flex items-center gap-1">
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

    {#each breadcrumbLevels as level, index (level.selected.id)}
        <MenuItem
            item={level.selected}
            siblings={level.siblings.length > 1 ? level.siblings : []}
        />
    {/each}
</div>
