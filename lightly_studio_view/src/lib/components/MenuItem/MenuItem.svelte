<script lang="ts">
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils/shadcn';
    import { ChevronDown } from '@lucide/svelte';
    import type { NavigationMenuItem } from '../NavigationMenu/types';

    const { item, siblings = [] }: { item: NavigationMenuItem; siblings?: NavigationMenuItem[] } =
        $props();

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
        icon={item.icon}
        buttonProps={{
            href: item.href,
            'data-testid': `navigation-menu-${item.title.toLowerCase()}`,
            class: cn(item.isSelected && 'bg-accent')
        }}
    >
        {item.title}
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
        <div class={cn('absolute z-50 min-w-[200px]', 'left-0 top-full pt-1')}>
            <div class="w-full min-w-[200px] rounded-md border bg-popover p-1 shadow-md">
                {#each siblings as sibling (sibling.id)}
                    <Button
                        icon={sibling.icon}
                        variant="ghost"
                        buttonProps={{
                            href: sibling.href,
                            'data-testid': `navigation-dropdown-${sibling.title.toLowerCase()}`,
                            class: cn('w-full justify-start', sibling.isSelected && 'bg-accent')
                        }}
                    >
                        {sibling.title}
                    </Button>
                {/each}
            </div>
        </div>
    {/if}
</div>
