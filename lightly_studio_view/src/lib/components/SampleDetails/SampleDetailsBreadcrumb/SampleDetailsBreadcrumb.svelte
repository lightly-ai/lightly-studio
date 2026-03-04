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
    import { page } from '$app/state';
    import { useAdjacentImages } from '$lib/hooks/useAdjacentImages/useAdjacentImages';

    const {
        rootCollection
    }: {
        rootCollection: Collection;
    } = $props();

    // Get datasetId and collectionType from URL params
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id!);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentImages({
            sampleId: page.params.sampleId,
            collectionId
        })
    );

    const samplePosition = $derived($sampleAdjacentQuery.data?.current_sample_position ?? 0);
    const totalCount = $derived($sampleAdjacentQuery.data?.total_count ?? 0);
</script>

<Breadcrumb class="mb-2" data-testid="sample-details-breadcrumb">
    <BreadcrumbList>
        <!-- Home -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toCollectionHome(datasetId, collectionType, datasetId)}
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
                href={routeHelpers.toCollectionHome(datasetId, collectionType, datasetId)}
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
                    {#if samplePosition && totalCount}
                        Sample {samplePosition} of {totalCount}
                    {:else}
                        Sample
                    {/if}
                </span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
