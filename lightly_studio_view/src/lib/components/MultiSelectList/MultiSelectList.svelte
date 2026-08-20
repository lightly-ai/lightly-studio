<script lang="ts">
    import { Check as CheckIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import * as Command from '$lib/components/ui/command';
    import { cn } from '$lib/utils';

    export interface MultiSelectItem {
        value: string;
        label: string;
    }

    interface Props {
        items: MultiSelectItem[];
        selectedIds: string[];
        onChange: (ids: string[]) => void;
        /** Show "X of Y selected" counter and Select all / Clear buttons. */
        showSelectAll?: boolean;
        itemNoun?: string;
        itemNounPlural?: string;
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
