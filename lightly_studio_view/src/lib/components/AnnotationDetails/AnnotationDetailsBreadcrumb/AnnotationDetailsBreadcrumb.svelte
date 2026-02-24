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
    import type { Collection } from '$lib/services/types';
    import { page } from '$app/state';
    import { useAdjacentAnnotations } from '$lib/hooks/useAdjacentAnnotations/useAdjacentAnnotations';

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
        useAdjacentAnnotations({
            sampleId: page.params.annotationId,
            collectionId: collectionId
        })
    );

    const samplePosition = $derived($sampleAdjacentQuery.data?.current_sample_position ?? 0);
    const totalCount = $derived($sampleAdjacentQuery.data?.total_count ?? 0);
</script>

<Breadcrumb class="mb-2">
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

        <!-- Annotations -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toAnnotations(datasetId, collectionType, collectionId)}
                class="flex items-center gap-2"
            >
                <ComponentIcon class="h-4 w-4" />
                <span class="hidden sm:inline">Annotations</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Annotation -->
        <BreadcrumbItem>
            <BreadcrumbPage class="flex items-center gap-2">
                <SquareDashed class="h-4 w-4" />
                <span class="max-w-[200px] truncate">
                    {#if samplePosition !== undefined}
                        Sample {samplePosition} of {totalCount}
                    {:else}
                        Sample
                    {/if}
                </span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
