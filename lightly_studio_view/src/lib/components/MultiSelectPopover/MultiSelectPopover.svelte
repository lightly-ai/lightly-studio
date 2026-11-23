<script lang="ts">
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import type { ComponentProps } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import { cn } from '$lib/utils';

    type ListProps = ComponentProps<typeof MultiSelectList>;

    /** A button that opens a searchable multi-select list in a popover. */
    interface Props {
        items: ListProps['items'];
        selectedIds: string[];
        onChange: (ids: string[]) => void;
        /** Text of the button, e.g. "3 tags selected". */
        label: string;
        itemNoun?: ListProps['itemNoun'];
        itemNounPlural?: ListProps['itemNounPlural'];
        showSelectAll?: ListProps['showSelectAll'];
        searchTestId?: ListProps['searchTestId'];
        disabled?: boolean;
        ariaLabel?: string;
        align?: ComponentProps<typeof Popover.Content>['align'];
        /** Extra classes for the button, e.g. its width or height. */
        triggerClass?: string;
        /** Extra classes for the popover, e.g. its width. */
        contentClass?: string;
        testId?: string;
    }

    const {
        items,
        selectedIds,
        onChange,
        label,
        itemNoun,
        itemNounPlural,
        showSelectAll = false,
        searchTestId,
        disabled = false,
        ariaLabel,
        align,
        triggerClass,
        contentClass,
        testId
    }: Props = $props();
    let open = $state(false);
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class={cn(
                    'h-8 min-w-0 justify-between gap-2 px-3 text-xs font-normal',
                    triggerClass
                )}
                role="combobox"
                aria-expanded={open}
                aria-label={ariaLabel}
                {disabled}
                data-testid={testId}
            >
                <span class="truncate">{label}</span>
                <ChevronDown class="size-4 shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class={cn('w-[280px] p-2', contentClass)} {align}>
        <MultiSelectList
            {items}
            {selectedIds}
            {onChange}
            {showSelectAll}
            {itemNoun}
            {itemNounPlural}
            {searchTestId}
        />
    </Popover.Content>
</Popover.Root>
