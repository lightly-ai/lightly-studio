<script lang="ts">
    import type { NavigationMenuItem, BreadcrumbLevel } from './types';
    import { findAncestorPath, buildBreadcrumbLevels as buildLevels } from './utils';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, WholeWord, Video, Frame, ComponentIcon, LayoutDashboard } from '@lucide/svelte';
    import { SampleType, type CollectionView } from '$lib/api/lightly_studio_local';
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

    function getMenuItem(
        sampleType: SampleType,
        pageId: string | null,
        datasetId: string,
        collectionType: string,
        collectionId: string
    ): NavigationMenuItem {
        switch (sampleType) {
            case SampleType.IMAGE:
                return {
                    title: 'Images',
                    id: `samples-${collectionId}`,
                    href: routeHelpers.toSamples(datasetId, collectionType, collectionId),
                    isSelected:
                        pageId === APP_ROUTES.samples || pageId === APP_ROUTES.sampleDetails,
                    icon: Image
                };

            case SampleType.VIDEO:
                return {
                    title: 'Videos',
                    id: `videos-${collectionId}`,
                    href: routeHelpers.toVideos(datasetId, collectionType, collectionId),
                    isSelected: pageId === APP_ROUTES.videos || pageId === APP_ROUTES.videoDetails,
                    icon: Video
                };
            case SampleType.VIDEO_FRAME:
                return {
                    title: 'Frames',
                    id: `frames-${collectionId}`,
                    icon: Frame,
                    href: routeHelpers.toFrames(datasetId, collectionType, collectionId),
                    isSelected: pageId == APP_ROUTES.frames || pageId == APP_ROUTES.framesDetails
                };
            case SampleType.ANNOTATION:
                return {
                    title: 'Annotations',
                    id: `annotations-${collectionId}`,
                    icon: ComponentIcon,
                    href: routeHelpers.toAnnotations(datasetId, collectionType, collectionId),
                    isSelected:
                        pageId == APP_ROUTES.annotations || pageId == APP_ROUTES.annotationDetails
                };
            case SampleType.CAPTION:
                return {
                    title: 'Captions',
                    id: `captions-${collectionId}`,
                    href: routeHelpers.toCaptions(datasetId, collectionType, collectionId),
                    isSelected: pageId === APP_ROUTES.captions,
                    icon: WholeWord
                };
            case SampleType.GROUP:
                return {
                    title: 'Groups',
                    id: 'groups',
                    href: routeHelpers.toGroups(datasetId, collectionType, collectionId),
                    isSelected: pageId === APP_ROUTES.groups,
                    icon: LayoutDashboard
                };
        }
    }

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

    // TODO(Michal, 02/2026): Remove this function after switching to new navigation.
    // It is a thin wrapper around getMenuItem to handle the `undefined` return case.
    const toMenuItem = (c: CollectionView): NavigationMenuItem => {
        const item = getMenuItem(
            c.sample_type,
            pageId,
            datasetId,
            c.sample_type.toLowerCase(),
            c.collection_id
        );
        if (!item) {
            throw new Error(`Unsupported sample type in navigation path: ${c.sample_type}`);
        }
        return item;
    };

    // TODO(Michal, 02/2026): Remove the eslint disable comment once used.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const breadcrumbLevels: BreadcrumbLevel[] = $derived(
        buildLevels(ancestorPath, collection, toMenuItem)
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
