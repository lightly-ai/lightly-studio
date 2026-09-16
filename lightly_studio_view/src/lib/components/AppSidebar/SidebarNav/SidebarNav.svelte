<script lang="ts">
    import { cn, formatInteger } from '$lib/utils';
    import type { SidebarNavItem } from './buildSidebarNavItems';

    interface Props {
        items: SidebarNavItem[];
    }

    const { items }: Props = $props();
</script>

<nav class="flex flex-col gap-px px-1.5 pb-1 pt-2" data-testid="navigation-menu">
    {#each items as item (item.id)}
        {@const Icon = item.icon}
        <a
            href={item.href}
            aria-current={item.isSelected ? 'page' : undefined}
            data-testid={`navigation-menu-${item.title.toLowerCase()}`}
            data-sidebar-nav-item
            class={cn(
                'flex h-[30px] items-center gap-[9px] rounded-md px-2 text-[13px] font-medium transition-colors',
                item.isSelected
                    ? 'bg-sidebar-accent text-foreground'
                    : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
            )}
        >
            {#if Icon}
                <Icon class="size-[15px] shrink-0" />
            {/if}
            <span class="min-w-0 flex-1 truncate text-left">{item.title}</span>
            {#if item.count !== undefined}
                <span class="text-[11px] tabular-nums text-muted-foreground">
                    {formatInteger(item.count)}
                </span>
            {/if}
        </a>
    {/each}
</nav>
