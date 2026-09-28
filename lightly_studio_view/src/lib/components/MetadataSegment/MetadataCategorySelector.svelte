<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';

    interface CategoryItem {
        value: string;
        label: string;
    }

    interface Props {
        items: CategoryItem[];
        selectedIds: string[] | null;
        onChange: (ids: string[]) => void;
    }

    const { items, selectedIds, onChange }: Props = $props();
    const selected = $derived(selectedIds ?? items.map(({ value }) => value));
    const label = $derived(
        selected.length === items.length
            ? 'All categories'
            : `${selected.length} categories selected`
    );
</script>

<Popover.Root>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class="h-8 w-full justify-between px-3 text-xs font-normal"
                role="combobox"
                aria-label="Choose metadata categories"
                data-testid="metadata-category-select"
            >
                <span class="truncate">{label}</span>
                <ChevronDown class="ml-2 size-4 shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="start">
        <MultiSelectList
            {items}
            selectedIds={selected}
            {onChange}
            showSelectAll
            itemNoun="category"
            itemNounPlural="categories"
            searchTestId="metadata-category-search"
        />
    </Popover.Content>
</Popover.Root>
