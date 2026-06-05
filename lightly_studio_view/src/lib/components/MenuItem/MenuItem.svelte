<script lang="ts">
    import { Button } from '$lib/components';
    import { Select } from '$lib/components/Select';
    import { goto } from '$app/navigation';
    import { cn } from '$lib/utils/shadcn';
    import type { NavigationMenuItem } from '../NavigationMenu/types';

    const { item, siblings = [] }: { item: NavigationMenuItem; siblings?: NavigationMenuItem[] } =
        $props();

    const hasSiblings = $derived(siblings.length > 0);

    const selectItems = $derived(
        siblings.map((sibling) => ({
            value: sibling.id,
            label: sibling.title,
            icon: sibling.icon,
            testId: `navigation-dropdown-${sibling.title.toLowerCase()}`,
            class: 'cursor-pointer'
        }))
    );

    let selectedValue = $state<string | undefined>(undefined);

    const handleValueChange = (value: string) => {
        const sibling = siblings.find((s) => s.id === value);
        selectedValue = undefined;
        if (sibling) {
            goto(sibling.href);
        }
    };
</script>

{#if hasSiblings}
    <Select
        bind:value={selectedValue}
        triggerLabel={item.title}
        icon={item.icon}
        items={selectItems}
        onValueChange={handleValueChange}
        class={cn('w-auto', item.isSelected && 'bg-accent')}
        testId={`navigation-menu-${item.title.toLowerCase()}`}
    />
{:else}
    <Button
        icon={item.icon}
        buttonProps={{
            href: item.href,
            'data-testid': `navigation-menu-${item.title.toLowerCase()}`,
            class: cn(item.isSelected && 'bg-accent')
        }}
    >
        {item.title}
    </Button>
{/if}
