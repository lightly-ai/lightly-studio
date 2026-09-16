<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { formatInteger } from '$lib/utils';
    import { PanelLeft, PanelLeftClose } from '@lucide/svelte';

    interface Props {
        /** View name, e.g. "Images". */
        title: string;
        /** Item count shown next to the title, omitted while loading. */
        count: number | undefined;
        sidebarCollapsed: boolean;
        onToggleSidebar: () => void;
        /** Controls aligned to the right: source select, overflow menu, avatar. */
        actions?: Snippet;
    }

    const { title, count, sidebarCollapsed, onToggleSidebar, actions }: Props = $props();
</script>

<header
    class="flex h-[52px] shrink-0 items-center gap-2.5 border-b border-border-hard px-2.5"
    data-testid="content-header"
>
    <Tooltip
        content={sidebarCollapsed ? 'Show filters' : 'Hide filters'}
        position="bottom"
        class="w-max"
    >
        <button
            class="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            onclick={onToggleSidebar}
            aria-expanded={!sidebarCollapsed}
            aria-label={sidebarCollapsed ? 'Show filters' : 'Hide filters'}
            data-testid="filter-panel-collapse"
        >
            {#if sidebarCollapsed}
                <PanelLeft class="size-[15px]" />
            {:else}
                <PanelLeftClose class="size-[15px]" />
            {/if}
        </button>
    </Tooltip>

    <div class="h-[18px] w-px bg-border-hard"></div>

    <h1 class="truncate text-sm font-semibold tracking-[-0.01em] text-foreground">{title}</h1>
    {#if count !== undefined}
        <span class="text-xs tabular-nums text-muted-foreground" data-testid="content-header-count">
            {formatInteger(count)}
        </span>
    {/if}

    <div class="flex-1"></div>

    {@render actions?.()}
</header>
