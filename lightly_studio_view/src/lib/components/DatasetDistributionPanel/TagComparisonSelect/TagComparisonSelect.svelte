<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import type { MultiSelectItem } from '$lib/components/MultiSelectList';

    interface Props {
        items: MultiSelectItem[];
        selectedIds: string[];
        onChange: (ids: string[]) => void;
    }

    const { items, selectedIds, onChange }: Props = $props();
    let open = $state(false);
    const label = $derived(
        selectedIds.length === 0
            ? 'Compare sample tags'
            : `${selectedIds.length} tag${selectedIds.length === 1 ? '' : 's'} selected`
    );
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class="m-0 h-8 min-w-0 flex-1 justify-start gap-2 rounded-md px-3 text-xs font-normal"
                role="combobox"
                aria-expanded={open}
                data-testid="dataset-distribution-tag-select"
            >
                <span class="truncate">{label}</span>
                <ChevronDown class="ml-auto size-4 shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[260px] p-0 pt-2">
        <MultiSelectList
            {items}
            {selectedIds}
            {onChange}
            itemNoun="sample tag"
            itemNounPlural="sample tags"
        />
    </Popover.Content>
</Popover.Root>
