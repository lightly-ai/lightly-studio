<script lang="ts">
    import { Check as CheckIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import * as Command from '$lib/components/ui/command';
    import { cn } from '$lib/utils';

    interface ManualSelectionItem {
        value: string;
        label: string;
    }

    interface Props {
        /** Currently selected class labels. Bindable — mutated on toggle / Select all / Clear. */
        selected: string[];
        /** Full list of class labels to choose from, in the order they should be displayed. */
        allClasses?: string[];
        /** Optional stable values and display labels; labels need not be unique. */
        items?: ManualSelectionItem[];
        itemNoun?: string;
        itemNounPlural?: string;
        /** test-id for the search input; lets each host keep its own id scheme. */
        searchTestId?: string;
    }

    let {
        selected = $bindable(),
        allClasses,
        items,
        itemNoun = 'class',
        itemNounPlural = 'classes',
        searchTestId
    }: Props = $props();

    const resolvedItems = $derived(
        items ?? (allClasses ?? []).map((className) => ({ value: className, label: className }))
    );

    const isSelected = (value: string) => selected.includes(value);

    const toggle = (value: string) => {
        selected = selected.includes(value)
            ? selected.filter((selectedValue) => selectedValue !== value)
            : [...selected, value];
    };
</script>

<div class="pt-2">
    <div class="mb-1 flex items-center justify-between">
        <span class="text-xs text-muted-foreground">
            {selected.length} of {resolvedItems.length} selected
        </span>
        <div class="flex gap-1">
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'h-6 px-2 text-xs',
                    onclick: () => (selected = resolvedItems.map((item) => item.value))
                }}
            >
                Select all
            </Button>
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'h-6 px-2 text-xs',
                    onclick: () => (selected = [])
                }}
            >
                Clear
            </Button>
        </div>
    </div>
    <Command.Root class="rounded-md border">
        <Command.Input placeholder="Search {itemNounPlural}..." data-testid={searchTestId} />
        <Command.List class="max-h-[220px] dark:[color-scheme:dark]">
            <Command.Empty>No {itemNoun} found.</Command.Empty>
            {#each resolvedItems as item (item.value)}
                <Command.Item
                    value={item.value}
                    keywords={[item.label]}
                    onSelect={() => toggle(item.value)}
                >
                    <CheckIcon class={cn(!isSelected(item.value) && 'text-transparent')} />
                    <span class="min-w-0 flex-1 truncate">{item.label}</span>
                </Command.Item>
            {/each}
        </Command.List>
    </Command.Root>
</div>
