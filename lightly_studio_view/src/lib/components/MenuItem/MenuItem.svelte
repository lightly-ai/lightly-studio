<script lang="ts">
    import { cn } from "$lib/utils/shadcn";
    import type { NavigationMenuItem } from "../NavigationMenu/types";
    import Button from "../ui/button/button.svelte";

    const {
        item,
    } : { item: NavigationMenuItem } = $props()
</script>

<Button
    variant="ghost"
    class={cn('nav-button flex items-center space-x-2', item.isSelected && 'bg-accent')}
    data-testid={`navigation-menu-${item.title.toLowerCase()}`}
    href={item.href}
    title={item.title}
>
    {#if item.icon}
        <item.icon class="size-4" />
    {/if}
    <span>{item.title}</span>
</Button>
