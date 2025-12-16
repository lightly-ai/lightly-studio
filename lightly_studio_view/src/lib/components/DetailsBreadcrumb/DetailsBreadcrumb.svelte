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
    import type { DatasetViewWithCount } from '$lib/api/lightly_studio_local';

    const {
        index,
        section,
        subsection,
        dataset,
        navigateTo
    }: {
        index?: number | null | undefined;
        section: string;
        subsection: string;
        dataset: DatasetViewWithCount;
        navigateTo: (dataset_id: string) => string;
    } = $props();

    const { filteredSampleCount } = useGlobalStorage();
</script>

<Breadcrumb class="mb-2">
    <BreadcrumbList>
        <BreadcrumbItem>
            <BreadcrumbLink href={routeHelpers.toHome()} class="flex items-center gap-2">
                <Home class="h-4 w-4" />
                <span class="hidden sm:inline">Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <BreadcrumbItem>
            <BreadcrumbLink href={navigateTo(dataset.collection_id!)} class="flex items-center gap-2">
                <Database class="h-4 w-4" />
                <span class="max-w-[150px] truncate">
                    {dataset.name}
                </span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <BreadcrumbItem>
            <BreadcrumbLink href={navigateTo(dataset.collection_id!)} class="flex items-center gap-2">
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
