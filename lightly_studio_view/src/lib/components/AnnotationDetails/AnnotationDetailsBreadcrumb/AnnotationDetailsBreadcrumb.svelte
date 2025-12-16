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
    import type { Dataset } from '$lib/services/types';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    const {
        dataset,
        annotationIndex
    }: {
        dataset: Dataset;
        annotationIndex?: number;
    } = $props();

    const { filteredAnnotationCount } = useGlobalStorage();
</script>

<Breadcrumb class="mb-2">
    <BreadcrumbList>
        <!-- Home -->
        <BreadcrumbItem>
            <BreadcrumbLink href={routeHelpers.toHome()} class="flex items-center gap-2">
                <Home class="h-4 w-4" />
                <span class="hidden sm:inline">Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Dataset -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toAnnotations(dataset.collection_id!)}
                class="flex items-center gap-2"
            >
                <Database class="h-4 w-4" />
                <span class="max-w-[150px] truncate">
                    {dataset.name}
                </span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />

        <!-- Annotations -->
        <BreadcrumbItem>
            <BreadcrumbLink
                href={routeHelpers.toAnnotations(dataset.collection_id!)}
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
                    {#if annotationIndex !== undefined}
                        Annotation {annotationIndex + 1} of {$filteredAnnotationCount}
                    {:else}
                        Annotation
                    {/if}
                </span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
