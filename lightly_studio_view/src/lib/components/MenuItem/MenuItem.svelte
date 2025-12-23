<script lang="ts">
    import MenuItem from './MenuItem.svelte';
    import { cn } from '$lib/utils/shadcn';
    import Button from '../ui/button/button.svelte';
    import { ChevronDown } from '@lucide/svelte';
    import type { NavigationMenuItem } from '../NavigationMenu/types';

    const { item, level = 0 }: { item: NavigationMenuItem; level?: number } = $props();

    let open = $state(false);
    const hasChildren = item.children?.length;
</script>

<div
    class={cn('relative inline-block', level > 0 && 'w-full min-w-[200px]')}
    onmouseenter={() => (open = true)}
    onmouseleave={() => (open = false)}
    onfocusin={() => (open = true)}
    onfocusout={() => (open = false)}
    role={'button'}
>
    <Button
        variant="ghost"
        class={cn(
            'flex items-center justify-between',
            level > 0 && 'w-full',
            item.isSelected && 'bg-accent'
        )}
        href={item.href}
        data-testid={`navigation-menu-${item.title.toLowerCase()}`}
    >
        <div class="flex items-center gap-2">
            {#if item.icon}
                <item.icon class="size-4 shrink-0" />
            {/if}
            <span>{item.title}</span>
        </div>

        {#if hasChildren}
            <ChevronDown
                class={cn(
                    'size-4 shrink-0 opacity-60 transition-transform duration-200',
                    open && 'rotate-180'
                )}
            />
        {/if}
    </Button>

    {#if hasChildren && open}
        <div
            class={cn(
                'absolute z-50 min-w-[200px]',
                level === 0 ? 'left-0 top-full pt-1' : 'left-full top-0 pl-1'
            )}
        >
            <div class="w-full min-w-[200px] rounded-md border bg-popover p-1 shadow-md">
                {#each item.children as child (child.id)}
                    <MenuItem item={child} level={level + 1} />
                {/each}
            </div>
        </div>
    {/if}
</div>
