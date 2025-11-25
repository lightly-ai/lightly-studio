<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { cn } from '$lib/utils';
    import type { NavigationMenuItem } from './types';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, WholeWord, Video, Frame } from '@lucide/svelte';
    import { SampleType, type DatasetView } from '$lib/api/lightly_studio_local';

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
                    title: 'Samples',
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
                    icon: Frame,
                    href: routeHelpers.toAnnotations(datasetId),
                    isSelected:
                        pageId == APP_ROUTES.annotatiosns || pageId == APP_ROUTES.annotationDetails
                };
            default:
                return undefined;
        }
    }

    const buildMenu = (): NavigationMenuItem[] => {
        let menuItem = getMenuItem(dataset.sample_type, pageId, dataset.dataset_id);
        if (!menuItem) return [];

        let children = dataset.children;

        let childrenItems = children
            ? children
                  ?.map((dataset2) => {
                      return getMenuItem(dataset2.sample_type, pageId, dataset2.dataset_id);
                  })
                  .filter((item) => item != undefined)
            : [];

        // This is required because we don't have multimodal support
        // for captions yet.
        if (dataset.sample_type == SampleType.IMAGE) {
            childrenItems = [
                ...childrenItems,
                {
                    title: 'Captions',
                    id: 'captions',
                    href: routeHelpers.toCaptions(dataset.dataset_id),
                    isSelected: pageId === APP_ROUTES.captions,
                    icon: WholeWord
                }
            ];
        }
        
        const allItems = [menuItem, ...childrenItems];
        
        return allItems;
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
