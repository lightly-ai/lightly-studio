<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { cn } from '$lib/utils';
    import type { NavigationMenuItem } from './types';
    import { APP_ROUTES, routeHelpers } from '$lib/routes';
    import { page } from '$app/state';
    import { Image, ComponentIcon, WholeWord } from '@lucide/svelte';

    const {
        datasetId
    }: {
        datasetId: string;
    } = $props();

    const pageId = $derived(page.route.id);
    const menuItems: NavigationMenuItem[] = $derived([
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
    ]);
</script>

<div class="flex gap-2">
    {#each menuItems as { title, href, isSelected, icon: Icon, id } (id)}
        <Button
            variant="ghost"
            class={cn('flex items-center space-x-2', isSelected && 'bg-accent')}
            data-testid={`navigation-menu-${title.toLowerCase()}`}
            {href}
        >
            {#if Icon}
                <Icon class="size-4" />
            {/if}
            {title}
        </Button>
    {/each}
</div>
