<script lang="ts">
    import type { Component, Snippet } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import * as SelectPrimitive from '$lib/components/ui/select';
    import { cn } from '$lib/utils/shadcn';

    export interface SelectItem {
        value: string;
        label: string;
        /** Optional Lucide icon rendered before the label, in both the trigger and dropdown. */
        icon?: Component<IconProps>;
        testId?: string;
    }

    export type SelectSize = 'sm' | 'md' | 'lg';

    interface Props {
        /** List of items to render. Mutually exclusive with `children` slot. */
        items?: SelectItem[];
        /** Currently selected value. */
        value?: string;
        /** Placeholder text shown when nothing is selected. */
        placeholder?: string;
        /** Allow clearing the current selection. */
        allowDeselect?: boolean;
        /** Whether the select is disabled. */
        disabled?: boolean;
        /** Whether the dropdown is open. Bindable for external control. */
        open?: boolean;
        /** Trigger size. Heights align with the Button primitive. */
        size?: SelectSize;
        /** Additional class names for the trigger button. */
        class?: string;
        /** `data-testid` for the trigger element. */
        testId?: string;
        /** Called when the selected value changes. */
        onValueChange?: (value: string) => void;
        /**
         * Advanced slot: provide custom `Select.Item` / `Select.Group` markup.
         * When provided, `items` prop is ignored.
         */
        children?: Snippet;
    }

    let {
        items,
        value = $bindable(undefined),
        placeholder = 'Select…',
        allowDeselect = false,
        disabled = false,
        open = $bindable(false),
        size = 'md',
        class: className,
        testId,
        onValueChange,
        children
    }: Props = $props();

    const triggerSizeClass: Record<SelectSize, string> = {
        sm: 'h-9 text-xs',
        md: 'h-10 text-sm',
        lg: 'h-11 text-base'
    };

    const itemSizeClass: Record<SelectSize, string> = {
        sm: 'py-1 text-xs',
        md: 'py-1.5 text-sm',
        lg: 'py-2 text-base'
    };

    const iconSizeClass: Record<SelectSize, string> = {
        sm: 'size-3.5',
        md: 'size-4',
        lg: 'size-5'
    };

    const findItem = (v: string | undefined) =>
        v === undefined ? undefined : items?.find((i) => i.value === v);

    const handleValueChange = (v: string) => {
        value = v;
        onValueChange?.(v);
    };
</script>

<SelectPrimitive.Root
    type="single"
    {value}
    {allowDeselect}
    {disabled}
    bind:open
    onValueChange={handleValueChange}
>
    <SelectPrimitive.Trigger
        data-testid={testId}
        class={cn(
            // Ghost-style: no border, no background, height matches the Button primitive
            'm-0 flex items-center gap-2 rounded-md border-0 bg-transparent pr-2 font-normal',
            triggerSizeClass[size],
            'text-foreground hover:bg-accent hover:text-accent-foreground',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'data-[placeholder]:text-muted-foreground',
            className
        )}
    >
        {@const selectedItem = findItem(value)}
        {#if selectedItem?.icon}
            {@const TriggerIcon = selectedItem.icon}
            <TriggerIcon class={cn(iconSizeClass[size], 'shrink-0')} />
        {/if}
        <span class="truncate">{value ? (selectedItem?.label ?? value) : placeholder}</span>
    </SelectPrimitive.Trigger>

    <SelectPrimitive.Content>
        {#if children}
            {@render children()}
        {:else if items}
            {#each items as item (item.value)}
                <SelectPrimitive.Item
                    value={item.value}
                    label={item.label}
                    data-testid={item.testId}
                    class={cn('gap-2', itemSizeClass[size])}
                >
                    {#if item.icon}
                        {@const ItemIcon = item.icon}
                        <ItemIcon class={cn(iconSizeClass[size], 'shrink-0')} />
                    {/if}
                    {item.label}
                </SelectPrimitive.Item>
            {/each}
        {/if}
    </SelectPrimitive.Content>
</SelectPrimitive.Root>
