<script lang="ts">
    import { cn } from '$lib/utils/shadcn';
    import Button from '../ui/button/button.svelte';
    import { ChevronDown } from '@lucide/svelte';
    import type { NavigationMenuItem } from '../NavigationMenu/types';

    const {
        item,
        siblings = []
    }: { item: NavigationMenuItem; siblings?: NavigationMenuItem[] } = $props();

    let open = $state(false);
    const hasSiblings = $derived(siblings.length > 0);
</script>

<div
    class="relative inline-block"
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

        {#if hasSiblings}
            <ChevronDown
                class={cn(
                    'size-4 shrink-0 opacity-60 transition-transform duration-200',
                    open && 'rotate-180'
                )}
            />
        {/if}
    </Button>

    {#if hasSiblings && open}
        <div
            class={cn(
                'absolute z-50 min-w-[200px]',
                'left-0 top-full pt-1'
            )}
        >
            <div class="w-full min-w-[200px] rounded-md border bg-popover p-1 shadow-md">
                {#each siblings as sibling (sibling.id)}
                    <Button
                        variant="ghost"
                        class={cn(
                            'flex w-full items-center gap-2 justify-start',
                            sibling.isSelected && 'bg-accent'
                        )}
                        href={sibling.href}
                    >
                        {#if sibling.icon}
                            <sibling.icon class="size-4 shrink-0" />
                        {/if}
                        <span>{sibling.title}</span>
                    </Button>
                {/each}
            </div>
        </div>
    {/if}
</div>
