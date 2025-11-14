<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { cn } from '$lib/utils';
    import type { NavigationMenuItem } from './types';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, ComponentIcon, WholeWord, Video, Frame } from '@lucide/svelte';
    import type { SampleType } from '$lib/api/lightly_studio_local';

    const {
        datasetId,
        sampleType
    }: {
        datasetId: string;
        sampleType?: SampleType;
    } = $props();

    const pageId = $derived(page.route.id);
    const imageMenu = () => [
        {
            title: 'Samples',
            id: 'samples',
            href: routeHelpers.toSamples(datasetId),
            isSelected:
                pageId === APP_ROUTES.samples ||
                pageId === APP_ROUTES.sampleDetails ||
                pageId === APP_ROUTES.sampleDetailsWithoutIndex,
            icon: Image
        },
        {
            title: 'Annotations',
            id: 'annotations',
            href: routeHelpers.toAnnotations(datasetId),
            isSelected:
                pageId === APP_ROUTES.annotations || pageId === APP_ROUTES.annotationDetails,
            icon: ComponentIcon
        },
        {
            title: 'Captions',
            id: 'captions',
            href: routeHelpers.toCaptions(datasetId),
            isSelected: pageId === APP_ROUTES.captions,
            icon: WholeWord
        }
    ];

    const videoMenu = () => [
        {
            title: 'Videos',
            id: 'videos',
            href: routeHelpers.toVideos(datasetId),
            isSelected: pageId === APP_ROUTES.videos,
            icon: Video
        },
        {
            title: 'Frames',
            id: 'frames',
            icon: Frame,
            href: routeHelpers.toFrames(datasetId),
            isSelected: pageId == APP_ROUTES.frames
        },
        {
            title: 'Annotations',
            id: 'annotations',
            href: routeHelpers.toAnnotations(datasetId),
            isSelected:
                pageId === APP_ROUTES.annotations || pageId === APP_ROUTES.annotationDetails,
            icon: ComponentIcon
        },
        {
            title: 'Captions',
            id: 'captions',
            href: routeHelpers.toCaptions(datasetId),
            isSelected: pageId === APP_ROUTES.captions,
            icon: WholeWord
        }
    ];
    const menuItems: NavigationMenuItem[] = $derived(
        sampleType == 'video' ? videoMenu() : imageMenu()
    );
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
