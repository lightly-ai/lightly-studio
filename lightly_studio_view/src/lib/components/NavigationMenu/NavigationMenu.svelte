<script lang="ts">
    import type { NavigationMenuItem } from './types';
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

    function getMenuItem(
        sampleType: SampleType,
        pageId: string | null,
        collectionId: string
    ): NavigationMenuItem | undefined {
        switch (sampleType) {
            case SampleType.IMAGE:
                return {
                    title: 'Images',
                    id: 'samples',
                    href: routeHelpers.toSamples(collectionId),
                    isSelected:
                        pageId === APP_ROUTES.samples ||
                        pageId === APP_ROUTES.sampleDetails ||
                        pageId === APP_ROUTES.sampleDetailsWithoutIndex,
                    icon: Image
                };

            case SampleType.VIDEO:
                return {
                    title: 'Videos',
                    id: 'videos',
                    href: routeHelpers.toVideos(collectionId),
                    isSelected: pageId === APP_ROUTES.videos || pageId === APP_ROUTES.videoDetails,
                    icon: Video
                };
            case SampleType.VIDEO_FRAME:
                return {
                    title: 'Frames',
                    id: 'frames',
                    icon: Frame,
                    href: routeHelpers.toFrames(collectionId),
                    isSelected: pageId == APP_ROUTES.frames || pageId == APP_ROUTES.framesDetails
                };
            case SampleType.ANNOTATION:
                return {
                    title: 'Annotations',
                    id: 'annotations',
                    icon: ComponentIcon,
                    href: routeHelpers.toAnnotations(collectionId),
                    isSelected:
                        pageId == APP_ROUTES.annotations || pageId == APP_ROUTES.annotationDetails
                };
            case SampleType.CAPTION:
                return {
                    title: 'Captions',
                    id: 'captions',
                    href: routeHelpers.toCaptions(collection.collection_id),
                    isSelected: pageId === APP_ROUTES.captions,
                    icon: WholeWord
                };
            default:
                return undefined;
        }
    }

    const buildMenu = (): NavigationMenuItem[] => {
        let menuItem = getMenuItem(collection.sample_type, pageId, collection.collection_id);
        if (!menuItem) return [];
        let children = collection.children;

        function buildItems(children: CollectionView[] | undefined): NavigationMenuItem[] {
            if (!children) return [];

            return children
                ?.map((child_collection) => {
                    const item = getMenuItem(
                        child_collection.sample_type,
                        pageId,
                        child_collection.collection_id
                    );

                    if (!item) return;

                    return {
                        ...item,
                        children: buildItems(child_collection.children ?? [])
                    };
                })
                .filter((item) => !!item);
        }

        let childrenItems = buildItems(children);

        return [menuItem, ...childrenItems];
    };

    const menuItems: NavigationMenuItem[] = $derived(buildMenu());

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
