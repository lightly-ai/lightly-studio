<script lang="ts">
    import type { NavigationMenuItem } from './types';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, WholeWord, Video, Frame, ComponentIcon } from '@lucide/svelte';
    import { SampleType, type DatasetView } from '$lib/api/lightly_studio_local';
    import MenuItem from '../MenuItem/MenuItem.svelte';

    const {
        dataset
    }: {
        dataset: DatasetView;
    } = $props();

    const pageId = $derived(page.route.id);

    function getMenuItem(
        sampleType: SampleType,
        pageId: string | null,
        datasetId: string
    ): NavigationMenuItem | undefined {
        switch (sampleType) {
            case SampleType.IMAGE:
                return {
                    title: 'Images',
                    id: 'samples',
                    href: routeHelpers.toSamples(datasetId),
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
                    href: routeHelpers.toVideos(datasetId),
                    isSelected: pageId === APP_ROUTES.videos || pageId === APP_ROUTES.videoDetails,
                    icon: Video
                };
            case SampleType.VIDEO_FRAME:
                return {
                    title: 'Frames',
                    id: 'frames',
                    icon: Frame,
                    href: routeHelpers.toFrames(datasetId),
                    isSelected: pageId == APP_ROUTES.frames || pageId == APP_ROUTES.frameDetails
                };
            case SampleType.ANNOTATION:
                return {
                    title: 'Annotations',
                    id: 'annotations',
                    icon: ComponentIcon,
                    href: routeHelpers.toAnnotations(datasetId),
                    isSelected:
                        pageId == APP_ROUTES.annotatiosns || pageId == APP_ROUTES.annotationDetails
                };
            case SampleType.CAPTION:
                return {
                    title: 'Captions',
                    id: 'captions',
                    href: routeHelpers.toCaptions(dataset.dataset_id),
                    isSelected: pageId === APP_ROUTES.captions,
                    icon: WholeWord
                };
            default:
                return undefined;
        }
    }

    const buildMenu = (): NavigationMenuItem[] => {
        let menuItem = getMenuItem(dataset.sample_type, pageId, dataset.dataset_id);
        if (!menuItem) return [];

        let children = dataset.children;

        function buildItems(children: DatasetView[] | undefined): NavigationMenuItem[] {
            if (!children) return [];

            return children
                ?.map((child_dataset) => {
                    const item = getMenuItem(
                        child_dataset.sample_type,
                        pageId,
                        child_dataset.dataset_id
                    );

                    if (!item) return;

                    return {
                        ...item,
                        children: buildItems(child_dataset.children ?? [])
                    };
                })
                .filter((item) => !!item);
        }

        let childrenItems = buildItems(children);

        return [menuItem, ...childrenItems];
    };

    const menuItems: NavigationMenuItem[] = $derived(buildMenu());
</script>

<div class="flex gap-2">
    {#each menuItems as item (item.id)}
        <MenuItem {item} />
    {/each}
</div>
