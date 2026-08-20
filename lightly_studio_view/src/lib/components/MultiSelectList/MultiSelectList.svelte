<script lang="ts">
    import { Check as CheckIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import * as Command from '$lib/components/ui/command';
    import { cn } from '$lib/utils';

    export interface MultiSelectItem {
        /** Unique identifier used as the selection key. */
        value: string;
        /** Display text shown in the list. */
        label: string;
    }

    interface Props {
        /** List of available options. */
        items: MultiSelectItem[];
        /** Values of currently selected items. */
        selectedIds: string[];
        /** Called with the new selection whenever an item is toggled, all selected, or cleared. */
        onChange: (ids: string[]) => void;
        /** Show "X of Y selected" counter and Select all / Clear buttons. */
        showSelectAll?: boolean;
        /** Singular noun used in the empty state and search placeholder (e.g. "tag"). */
        itemNoun?: string;
        /** Plural noun used in the empty state and search placeholder (e.g. "tags"). */
        itemNounPlural?: string;
        /** `data-testid` applied to the search input. */
        searchTestId?: string;
    }

    const {
        items,
        selectedIds,
        onChange,
        showSelectAll = false,
        itemNoun = 'item',
        itemNounPlural = 'items',
        searchTestId
    }: Props = $props();
</script>

<div>
    {#if showSelectAll}
        <div class="mb-1 flex items-center justify-between">
            <span class="text-xs text-muted-foreground">
                {selectedIds.length} of {items.length} selected
            </span>
            <div class="flex gap-1">
                <Button
                    variant="ghost"
                    buttonProps={{
                        size: 'sm',
                        class: 'h-6 px-2 text-xs',
                        onclick: () => onChange(items.map((item) => item.value))
                    }}
                >
                    Select all
                </Button>
                <Button
                    variant="ghost"
                    buttonProps={{
                        size: 'sm',
                        class: 'h-6 px-2 text-xs',
                        onclick: () => onChange([])
                    }}
                >
                    Clear
                </Button>
            </div>
        </div>
    {/if}
    <Command.Root class="rounded-md border">
        <Command.Input placeholder="Search {itemNounPlural}..." data-testid={searchTestId} />
        <Command.List class="max-h-[220px] dark:[color-scheme:dark]">
            <Command.Empty>No {itemNoun} found.</Command.Empty>
            {#each items as item (item.value)}
                <Command.Item
                    value={item.value}
                    keywords={[item.label]}
                    onSelect={() =>
                        onChange(
                            selectedIds.includes(item.value)
                                ? selectedIds.filter((id) => id !== item.value)
                                : [...selectedIds, item.value]
                        )}
                >
                    <CheckIcon
                        class={cn(!selectedIds.includes(item.value) && 'text-transparent')}
                    />
                    <span class="min-w-0 flex-1 truncate">{item.label}</span>
                </Command.Item>
            {/each}
        </Command.List>
    </Command.Root>
</div>
