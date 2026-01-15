<script lang="ts">
    import {
        Breadcrumb,
        BreadcrumbItem,
        BreadcrumbLink,
        BreadcrumbList,
        BreadcrumbPage,
        BreadcrumbSeparator
    } from '$lib/components/ui/breadcrumb/index.js';
    import { routeHelpers } from '$lib/routes';
    import { Home, Database, ComponentIcon, SquareDashed } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
    import { page } from '$app/state';

    const {
        index,
        section,
        subsection,
        rootCollection,
        navigateTo
    }: {
        index?: number | null | undefined;
        section: string;
        subsection: string;
        rootCollection: CollectionViewWithCount;
        navigateTo: (collection_id: string) => string;
    } = $props();

    const { filteredSampleCount } = useGlobalStorage();

    // Get datasetId and collectionType from URL params if available, otherwise use rootCollection
    const datasetId = $derived(page.params.dataset_id ?? rootCollection.collection_id!);
    const collectionType = $derived(page.params.collection_type ?? rootCollection.sample_type);
    const collectionId = $derived(page.params.collection_id ?? rootCollection.collection_id!);
</script>

<Breadcrumb class="mb-2">
    <BreadcrumbList>
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toCollectionHome(
                    datasetId,
                    collectionType,
                    rootCollection.collection_id!
                )}
                class="flex items-center gap-2"
            >
                <Home class="h-4 w-4" />
                <span class="hidden sm:inline">Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toCollectionHome(
                    datasetId,
                    collectionType,
                    rootCollection.collection_id!
                )}
                class="flex items-center gap-2"
            >
                <Database class="h-4 w-4" />
                <span class="max-w-[150px] truncate">
                    {rootCollection.name}
                </span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <BreadcrumbItem>
            <BreadcrumbLink href={navigateTo(collectionId)} class="flex items-center gap-2">
                <ComponentIcon class="h-4 w-4" />
                <span class="hidden sm:inline">{section}</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <BreadcrumbItem>
            <BreadcrumbPage class="flex items-center gap-2">
                <SquareDashed class="h-4 w-4" />
                <span class="max-w-[200px] truncate">
                    {#if index != undefined && $filteredSampleCount > 0}
                        {subsection} {index + 1} of {$filteredSampleCount}
                    {:else}
                        {subsection}
                    {/if}
                </span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
