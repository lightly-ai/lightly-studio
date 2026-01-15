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
    import { Home, Database, Images, FileImage } from '@lucide/svelte';
    import type { Collection } from '$lib/services/types';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { page } from '$app/state';

    const {
        rootCollection,
        sampleIndex
    }: {
        rootCollection: Collection;
        sampleIndex?: number;
    } = $props();

    const { filteredSampleCount } = useGlobalStorage();
    // Get datasetId and collectionType from URL params if available, otherwise use rootCollection
    const datasetId = $derived(page.params.dataset_id ?? rootCollection.collection_id!);
    const collectionType = $derived(page.params.collection_type ?? rootCollection.sample_type);
    const collectionId = $derived(page.params.collection_id ?? rootCollection.collection_id!);
</script>

<Breadcrumb class="mb-2" data-testid="sample-details-breadcrumb">
    <BreadcrumbList>
        <!-- Home -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toCollectionHome(datasetId, collectionType, rootCollection.collection_id!)}
                class="flex items-center gap-2"
            >
                <Home class="h-4 w-4" />
                <span class="hidden sm:inline">Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Collection -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toCollectionHome(datasetId, collectionType, rootCollection.collection_id!)}
                class="flex items-center gap-2"
            >
                <Database class="h-4 w-4" />
                <span class="max-w-[150px] truncate">
                    {rootCollection.name}
                </span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Samples -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toSamples(datasetId, collectionType, collectionId)}
                class="flex items-center gap-2"
            >
                <Images class="h-4 w-4" />
                <span class="hidden sm:inline">Samples</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Sample -->
        <BreadcrumbItem>
            <BreadcrumbPage class="flex items-center gap-2">
                <FileImage class="h-4 w-4" />
                <span class="max-w-[200px] truncate">
                    {#if sampleIndex !== undefined}
                        Sample {sampleIndex + 1} of {$filteredSampleCount}
                    {:else}
                        Sample
                    {/if}
                </span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
