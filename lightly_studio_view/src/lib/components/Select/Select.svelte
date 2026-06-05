<script lang="ts">
    import type { Component, Snippet } from 'svelte';
    import { Select as SelectBits, type WithoutChild } from 'bits-ui';
    import type { IconProps } from '@lucide/svelte';
    import * as SelectPrimitive from '$lib/components/ui/select';
    import { cn } from '$lib/utils/shadcn';

    type SelectTriggerProps = Omit<
        WithoutChild<SelectBits.TriggerProps>,
        'class' | 'data-testid' | 'ref'
    >;

    export interface SelectItem {
        value: string;
        label: string;
        /** Optional Lucide icon rendered before the label, in both the trigger and dropdown. */
        icon?: Component<IconProps>;
        /** Disable this item in the dropdown. */
        disabled?: boolean;
        testId?: string;
        /** Additional class names applied to the dropdown item. */
        class?: string;
    }

    export type SelectSize = 'xs' | 'sm' | 'md' | 'lg';

    interface Props {
        /** List of items to render. Mutually exclusive with `children` slot. */
        items?: SelectItem[];
        /** Currently selected value. */
        value?: string;
        /** Placeholder text shown when nothing is selected. */
        placeholder?: string;
        /** Fixed label shown in the trigger instead of the selected value's label. */
        triggerLabel?: string;
        /** Icon rendered in the trigger, irrespective of the current selection. */
        icon?: Component<IconProps>;
        /** Allow clearing the current selection. */
        allowDeselect?: boolean;
        /** Whether the select is disabled. */
        disabled?: boolean;
        /** Whether the dropdown is open. Bindable for external control. */
        open?: boolean;
        /** Trigger size. Heights align with the Button primitive. */
        size?: SelectSize;
        /** Skip reserving the left padding for the selection check marker on items. */
        hideSelectionMarker?: boolean;
        /** Render items as links (uses pointer cursor instead of the default select caret). */
        itemsAsLinks?: boolean;
        /** Additional class names for the trigger button. */
        class?: string;
        /** `data-testid` for the trigger element. */
        testId?: string;
        /** Additional attributes forwarded to the trigger button (e.g. `id` for `<Label for>`). */
        selectProps?: SelectTriggerProps;
        /** Called when the selected value changes. */
        onValueChange?: (value: string) => void;
        /** Called when the dropdown open state changes. */
        onOpenChange?: (open: boolean) => void;
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
        triggerLabel,
        icon: TriggerIconProp,
        allowDeselect = false,
        disabled = false,
        open = $bindable(false),
        size = 'md',
        hideSelectionMarker = false,
        itemsAsLinks = false,
        class: className,
        testId,
        selectProps,
        onValueChange,
        onOpenChange,
        children
    }: Props = $props();

    const triggerSizeClass: Record<SelectSize, string> = {
        xs: 'h-8 text-xs',
        sm: 'h-9 text-xs',
        md: 'h-10 text-sm',
        lg: 'h-11 text-base'
    };

    const itemSizeClass: Record<SelectSize, string> = {
        xs: 'py-1 text-xs',
        sm: 'py-1 text-xs',
        md: 'py-1.5 text-sm',
        lg: 'py-2 text-base'
    };

    const iconSizeClass: Record<SelectSize, string> = {
        xs: 'size-3.5',
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
    {items}
    {allowDeselect}
    {disabled}
    bind:open
    onValueChange={handleValueChange}
    {onOpenChange}
>
    <SelectPrimitive.Trigger
        {...selectProps}
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
        {@const TriggerIcon = TriggerIconProp ?? selectedItem?.icon}
        {#if TriggerIcon}
            <TriggerIcon class={cn(iconSizeClass[size], 'shrink-0')} />
        {/if}
        <span class="truncate"
            >{triggerLabel ?? (value ? (selectedItem?.label ?? value) : placeholder)}</span
        >
    </SelectPrimitive.Trigger>

    <SelectPrimitive.Content>
        {#if children}
            {@render children()}
        {:else if items}
            {#each items as item (item.value)}
                <SelectPrimitive.Item
                    value={item.value}
                    label={item.label}
                    disabled={item.disabled}
                    data-testid={item.testId}
                    class={cn(
                        'gap-2 pr-3',
                        itemSizeClass[size],
                        hideSelectionMarker && 'pl-2',
                        itemsAsLinks && 'cursor-pointer',
                        item.class
                    )}
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
