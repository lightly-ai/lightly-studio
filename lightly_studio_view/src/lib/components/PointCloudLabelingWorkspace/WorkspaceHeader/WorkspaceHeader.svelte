<script lang="ts">
    import { Boxes, Database, Home, Maximize2, Minimize2, X } from '@lucide/svelte';
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
        sampleId: string;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        isFullscreen: boolean;
        onToggleFullscreen: () => void;
        onExit: () => void;
    }

    let { sampleId, sourcePath = [], isFullscreen, onToggleFullscreen, onExit }: Props = $props();

    const iconFor = (index: number) => {
        if (index === 0) return Home;
        return index === sourcePath.length - 1 ? Boxes : Database;
    };
</script>

<header
    class="flex h-11 shrink-0 items-center justify-between gap-3 border-b bg-background px-3"
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
            <span class="truncate text-xs text-muted-foreground">· {sampleId}</span>
        </div>
    {/if}
    <div class="flex shrink-0 items-center gap-1">
        <Button
            variant="ghost"
            icon={isFullscreen ? Minimize2 : Maximize2}
            ariaLabel={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            buttonProps={{ onclick: onToggleFullscreen, size: 'sm', class: 'h-8 w-8 p-0' }}
        />
        <Button
            variant="ghost"
            icon={X}
            ariaLabel="Close labeling workspace"
            buttonProps={{ onclick: onExit, size: 'sm', class: 'h-8 w-8 p-0' }}
        />
    </div>
</header>
