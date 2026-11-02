<script lang="ts">
    import { Boxes, ComponentIcon, Database, Home } from '@lucide/svelte';
    import {
        Breadcrumb,
        BreadcrumbItem,
        BreadcrumbLink,
        BreadcrumbList,
        BreadcrumbPage,
        BreadcrumbSeparator
    } from '$lib/components/ui/breadcrumb';
    import type { WorkspaceCrumb } from '../types';
    /** Breadcrumb path displayed above the labeling workspace. */
    interface Props {
        /** Sequence used in the empty-path fallback. */
        sequenceId: string;
        /** Source path from dataset to sequence. */
        sourcePath: readonly WorkspaceCrumb[];
    }
    let { sequenceId, sourcePath }: Props = $props();
    const icons = [Home, Database, ComponentIcon, Boxes];
    const iconFor = (index: number) => icons[Math.min(index, icons.length - 1)];
</script>

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
                            <span>{crumb.label}</span>
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
