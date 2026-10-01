<script lang="ts">
    import { Boxes, ComponentIcon, Database, Home, Maximize2, Minimize2 } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import {
        Breadcrumb,
        BreadcrumbItem,
        BreadcrumbLink,
        BreadcrumbList,
        BreadcrumbPage,
        BreadcrumbSeparator
    } from '$lib/components/ui/breadcrumb/index.js';
    import type { WorkspaceCrumb } from '../types';

    interface Props {
        sequenceId: string;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        isFullscreen: boolean;
        onToggleFullscreen: () => void;
    }

    let { sequenceId, sourcePath = [], isFullscreen, onToggleFullscreen }: Props = $props();

    const iconFor = (index: number) => {
        if (index === 0) return Home;
        if (index === 1) return Database;
        if (index === 2) return ComponentIcon;
        return Boxes;
    };
</script>

<header
    class="flex shrink-0 items-center justify-between border-b pb-2"
    data-testid="workspace-header"
>
    {#if sourcePath.length > 0}
        <Breadcrumb data-testid="workspace-breadcrumb">
            <BreadcrumbList>
                {#each sourcePath as crumb, index (crumb.label + index)}
                    {@const Icon = iconFor(index)}
                    <BreadcrumbItem>
                        {#if crumb.href}
                            <BreadcrumbLink href={crumb.href} class="flex items-center gap-2">
                                <Icon class="h-4 w-4" />
                                <span class="max-w-[180px] truncate">{crumb.label}</span>
                            </BreadcrumbLink>
                        {:else}
                            <BreadcrumbPage class="flex items-center gap-2">
                                <Icon class="h-4 w-4" />
                                <span class="max-w-[220px] truncate">{crumb.label}</span>
                            </BreadcrumbPage>
                        {/if}
                    </BreadcrumbItem>
                    {#if index < sourcePath.length - 1}
                        <BreadcrumbSeparator />
                    {/if}
                {/each}
            </BreadcrumbList>
        </Breadcrumb>
    {:else}
        <div class="flex items-center gap-2 truncate text-sm font-medium">
            <span class="truncate">Point-cloud labeling</span>
            <span class="truncate text-xs text-muted-foreground">· {sequenceId}</span>
        </div>
    {/if}
    <div class="flex shrink-0 items-center gap-1">
        <Button
            variant="ghost"
            icon={isFullscreen ? Minimize2 : Maximize2}
            ariaLabel={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            buttonProps={{ onclick: onToggleFullscreen, size: 'sm', class: 'h-8 w-8 p-0' }}
        />
    </div>
</header>
