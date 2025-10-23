<script lang="ts">
    import CheckIcon from '@lucide/svelte/icons/check';
    import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
    import { tick, type Snippet } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { cn } from '$lib/utils';
    import type { ListItem } from './types';
    import Loader2Icon from '@lucide/svelte/icons/loader-2';

    let open = $state(false);

    let triggerRef = $state<HTMLButtonElement>(null!);

    // We want to refocus the trigger button when the user selects
    // an item from the list so users can continue navigating the
    // rest of the form with the keyboard.
    function closeAndFocusTrigger() {
        open = false;
        tick().then(() => {
            triggerRef.focus();
        });
    }

    type ChildProps = {
        props: Record<string, unknown>;
    };

    let {
        items,
        name = 'items',
        label = 'Select an item',
        selectedItem = $bindable<ListItem | undefined>(undefined),
        placeholder = 'Search an item...',
        onSelect,
        notFound,
        className = '',
        disabled = false,
        isLoading = false
    }: {
        placeholder?: string;
        name?: string;
        label?: string;
        className?: string;
        selectedItem?: ListItem;
        items: ListItem[];
        notFound?: Snippet<[{ inputValue: string }]>;
        onSelect?: (item: ListItem) => void;
        disabled?: boolean;
        isLoading?: boolean;
    } = $props();

    let inputValue = $state('');
    let highlightedValue = $state('');

    const selectedValue = $derived(selectedItem?.value);

    $effect(() => {
        if (!open) {
            inputValue = '';
            highlightedValue = '';
        }
    });

    const handleOnSelect = (item: ListItem) => {
        selectedItem = item;
        onSelect?.(item);
        closeAndFocusTrigger();
    };

    const createNewItem = (item: string) => {
        const existingItem = items.find(
            (i) => i.value.toLowerCase() === item.toLowerCase()
        );

        if (existingItem) {
            handleOnSelect(existingItem);
        } else {
            const newItem = { value: item, label: item };
            items.push(newItem);
            handleOnSelect(newItem);
        }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter') {
            if (highlightedValue) {
                const highlightedItem = items.find((item) => item.value === highlightedValue);
                if (highlightedItem) {
                    handleOnSelect(highlightedItem);
                    event.preventDefault();
                    return;
                }
            }

            if (inputValue) {
                createNewItem(inputValue);
                event.preventDefault();
            }
        }

        event.stopPropagation();
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger bind:ref={triggerRef}>
        {#snippet child({ props }: ChildProps)}
            <div class="flex items-center space-x-4">
                <Button
                    {...props}
                    variant="secondary"
                    {disabled}
                    class={cn('w-[200px] justify-between', className)}
                    role="combobox"
                    aria-expanded={open}
                    data-testid="select-list-trigger"
                >
                    {selectedItem?.label || label}
                    <ChevronsUpDownIcon class="opacity-50" />
                </Button>
                {#if isLoading}
                    <Loader2Icon class="mr-2 h-4 w-4 animate-spin" />
                {/if}
            </div>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[200px] p-0">
        <Command.Root bind:value={highlightedValue}>
            <Command.Input
                {placeholder}
                onkeydown={handleKeyDown}
                data-testid="select-list-input"
                bind:value={inputValue}
            />
            <Command.List class="dark:[color-scheme:dark]">
                <Command.Empty>
                    {#if notFound}
                        {@render notFound({
                            inputValue: inputValue || ''
                        })}
                    {:else}
                        Item not found
                    {/if}
                </Command.Empty>
                <Command.Group value={name}>
                    {#each items as item (item.value)}
                        <Command.Item value={item.value} onSelect={() => handleOnSelect(item)}>
                            <CheckIcon
                                class={cn(selectedValue !== item.value && 'text-transparent')}
                            />
                            {item.label}
                        </Command.Item>
                    {/each}
                </Command.Group>
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
