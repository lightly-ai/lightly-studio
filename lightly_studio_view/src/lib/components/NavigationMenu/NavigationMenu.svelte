<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { cn } from '$lib/utils';
    import type { NavigationMenuItem } from './types';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, WholeWord, Video, Frame, ComponentIcon } from '@lucide/svelte';
    import { SampleType, type CollectionView } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

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

        let childrenItems = children
            ? children
                  ?.map((child_collection) =>
                      getMenuItem(
                          child_collection.sample_type,
                          pageId,
                          child_collection.collection_id
                      )
                  )
                  .filter((item) => item != undefined)
            : [];

        return [menuItem, ...childrenItems];
    };

    const menuItems: NavigationMenuItem[] = $derived(buildMenu());
</script>

<div class="flex gap-2">
    {#each menuItems as { title, href, isSelected, icon: Icon, id } (id)}
        <Button
            variant="ghost"
            class={cn('nav-button flex items-center space-x-2', isSelected && 'bg-accent')}
            data-testid={`navigation-menu-${title.toLowerCase()}`}
            {href}
            {title}
        >
            {#if Icon}
                <Icon class="size-4" />
            {/if}
            <span>{title}</span>
        </Button>
    {/each}
</div>
