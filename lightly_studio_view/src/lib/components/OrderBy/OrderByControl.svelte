<script lang="ts">
    import { SortDirection } from '$lib/api/lightly_studio_local';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { ArrowDown, ArrowUp } from '@lucide/svelte';

    interface Props {
        items: SelectItem[];
        /** Value of the selected item, empty when nothing is sorted on. */
        selectedValue: string;
        /** Fixed trigger label, shown instead of the selected item's label. */
        triggerLabel?: string;
        direction: SortDirection;
        disabled?: boolean;
        allowDeselect?: boolean;
        onValueChange: (value: string) => void;
        onOpen: () => void;
        onToggleDirection: () => void;
    }

    const {
        items,
        selectedValue,
        triggerLabel,
        direction,
        disabled = false,
        allowDeselect = false,
        onValueChange,
        onOpen,
        onToggleDirection
    }: Props = $props();

    const directionTooltip = $derived(
        direction === SortDirection.DESC ? 'Sort descending' : 'Sort ascending'
    );
</script>

<div class="flex items-center gap-1">
    <Tooltip content="Sort items by attribute" position="top" triggerClass="inline-flex">
        <Select
            {items}
            value={selectedValue}
            {triggerLabel}
            {allowDeselect}
            {onValueChange}
            onOpenChange={(open) => {
                if (open) onOpen();
            }}
            {disabled}
            placeholder="Sort by"
            size="xs"
            variant="ghost"
            class="w-[100px] min-w-20"
            testId="sort-by-trigger"
        />
    </Tooltip>

    <Tooltip content={directionTooltip} position="top">
        <Button
            variant="ghost"
            icon={direction === SortDirection.DESC ? ArrowDown : ArrowUp}
            ariaLabel={directionTooltip}
            buttonProps={{
                size: 'icon',
                disabled: !triggerLabel || disabled,
                onclick: onToggleDirection,
                class: 'size-auto p-0 hover:bg-transparent [&>svg]:text-foreground [&>svg]:hover:text-muted-foreground',
                'data-testid': 'sort-direction-button'
            }}
        />
    </Tooltip>
</div>
