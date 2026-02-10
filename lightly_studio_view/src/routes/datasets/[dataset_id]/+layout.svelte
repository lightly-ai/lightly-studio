<script lang="ts">
    import { page } from '$app/stores';
    import { LayoutDashboard, Component } from '@lucide/svelte';
    import Button from '$lib/components/ui/button/button.svelte';
    import { cn } from '$lib/utils/shadcn';

    const { children } = $props();

    const datasetId = $derived($page.params.dataset_id);
    const currentPath = $derived($page.url.pathname);

    const isGroupsActive = $derived(currentPath.includes('/groups'));
    const isComponentsActive = $derived(currentPath.includes('/components'));
</script>

<div class="flex h-full flex-col">
    <header class="border-b border-border-hard bg-card px-4 py-3">
        <nav class="flex gap-2">
            <Button
                variant="ghost"
                class={cn('flex items-center gap-2', isGroupsActive && 'bg-accent')}
                href={`/datasets/${datasetId}/groups`}
                data-testid="navigation-menu-groups"
            >
                <LayoutDashboard class="size-4 shrink-0" />
                <span>Groups</span>
            </Button>

            <Button
                variant="ghost"
                class={cn('flex items-center gap-2', isComponentsActive && 'bg-accent')}
                href={`/datasets/${datasetId}/components`}
                data-testid="navigation-menu-components"
            >
                <Component class="size-4 shrink-0" />
                <span>Components</span>
            </Button>
        </nav>
    </header>

    <div class="flex-1 overflow-hidden">
        {@render children()}
    </div>
</div>
