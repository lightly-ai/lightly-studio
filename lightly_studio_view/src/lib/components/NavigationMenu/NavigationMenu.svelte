<script lang="ts">
    import type { NavigationMenuItem, BreadcrumbLevel } from './types';
    import { findAncestorPath, buildBreadcrumbLevels as buildLevels, getMenuItem } from './utils';
    import { page } from '$app/state';
    import { LayoutDashboard } from '@lucide/svelte';
    import { type CollectionView } from '$lib/api/lightly_studio_local';
    import MenuItem from '../MenuItem/MenuItem.svelte';
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

    const buildMenu = (): NavigationMenuItem[] => {
        const menuItem = getMenuItem(
            collection.sample_type,
            pageId,
            datasetId,
            collection.sample_type.toLowerCase(),
            collection.collection_id
        );

        function buildItems(children: CollectionView[] | undefined): NavigationMenuItem[] {
            if (!children) return [];

            return children.map((child_collection) => {
                const item = getMenuItem(
                    child_collection.sample_type,
                    pageId,
                    datasetId, // Same datasetId for all children
                    child_collection.sample_type.toLowerCase(),
                    child_collection.collection_id
                );

                return {
                    ...item,
                    children: buildItems(child_collection.children ?? [])
                };
            });
        }

        return [menuItem, ...buildItems(collection.children)];
    };

    const menuItems: NavigationMenuItem[] = $derived(buildMenu());

    const currentCollectionId = $derived(page.params.collection_id);

    const ancestorPath = $derived(
        currentCollectionId ? findAncestorPath(collection, currentCollectionId) : null
    );

    // TODO(Michal, 02/2026): Remove the eslint disable comment once used.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const breadcrumbLevels: BreadcrumbLevel[] = $derived(
        buildLevels(ancestorPath, collection, pageId, datasetId)
    );

    const { user } = useAuth();
</script>

<div class="flex gap-2">
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

    {#each menuItems as item (item.id)}
        <MenuItem {item} />
    {/each}
</div>
