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
    import type { Dataset } from '$lib/services/types';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { page } from '$app/state';

    const {
        rootDataset,
        sampleIndex
    }: {
        rootDataset: Dataset;
        sampleIndex?: number;
    } = $props();

    const { filteredSampleCount } = useGlobalStorage();
</script>

<Breadcrumb class="mb-2" data-testid="sample-details-breadcrumb">
    <BreadcrumbList>
        <!-- Home -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toDatasetHome(rootDataset.dataset_id!)}
                class="flex items-center gap-2"
            >
                <Home class="h-4 w-4" />
                <span class="hidden sm:inline">Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Dataset -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toDatasetHome(rootDataset.collection_id!)}
                class="flex items-center gap-2"
            >
                <Database class="h-4 w-4" />
                <span class="max-w-[150px] truncate">
                    {rootDataset.name}
                </span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Samples -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toSamples(page.params.collection_id)}
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
