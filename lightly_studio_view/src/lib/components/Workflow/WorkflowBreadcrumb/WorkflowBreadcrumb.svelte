<script lang="ts">
    import {
        Breadcrumb,
        BreadcrumbItem,
        BreadcrumbLink,
        BreadcrumbList,
        BreadcrumbPage,
        BreadcrumbSeparator
    } from '$lib/components/ui/breadcrumb/index.js';
    import type { WorkflowFile } from '$lib/hooks';
    import FileImage from '@lucide/svelte/icons/file-image';
    import FolderOpen from '@lucide/svelte/icons/folder-open';
    import Home from '@lucide/svelte/icons/home';
    import Layers from '@lucide/svelte/icons/layers';

    interface Props {
        file: Pick<
            WorkflowFile,
            'project_id' | 'project_name' | 'batch_id' | 'batch_name' | 'position' | 'total'
        >;
    }

    const { file }: Props = $props();

    // The project pages live in the hosted workspace app on the same origin.
    const projectHref = $derived(`/workspace/projects/${file.project_id}`);
</script>

<Breadcrumb class="mb-2" data-testid="workflow-breadcrumb">
    <BreadcrumbList>
        <BreadcrumbItem>
            <BreadcrumbLink
                href="/workspace/projects"
                data-sveltekit-reload
                class="flex items-center gap-2"
            >
                <Home class="h-4 w-4" />
                <span>Home</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
            <BreadcrumbLink
                href={projectHref}
                data-sveltekit-reload
                class="flex items-center gap-2"
            >
                <Layers class="h-4 w-4" />
                <span class="max-w-[150px] truncate">{file.project_name}</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
            <BreadcrumbLink
                href={`${projectHref}/batches/${file.batch_id}`}
                data-sveltekit-reload
                class="flex items-center gap-2"
            >
                <FolderOpen class="h-4 w-4" />
                <span class="max-w-[150px] truncate">{file.batch_name}</span>
            </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
            <BreadcrumbPage class="flex items-center gap-2">
                <FileImage class="h-4 w-4" />
                <span>Sample {file.position} of {file.total}</span>
            </BreadcrumbPage>
        </BreadcrumbItem>
    </BreadcrumbList>
</Breadcrumb>
