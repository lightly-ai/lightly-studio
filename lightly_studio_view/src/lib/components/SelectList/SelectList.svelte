<script lang="ts">
    import {
        Check as CheckIcon,
        ChevronsUpDown as ChevronsUpDownIcon,
        LoaderCircle as Loader2Icon
    } from '@lucide/svelte';
    import { tick, untrack, type Snippet } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { cn } from '$lib/utils';
    import type { ListItem } from './types';

    let triggerRef = $state<HTMLButtonElement>(null!);
    let inputRef = $state<HTMLInputElement>(null!);

    // We want to refocus the trigger button when the user selects
    // an item from the list so users can continue navigating the
    // rest of the form with the keyboard.
    function closeAndFocusTrigger() {
        open = false;
        tick().then(() => {
            triggerRef?.focus();
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
        contentClassName = '',
        autoOpen = false,
        autoFocus = false,
        disabled = false,
        isLoading = false,
        onKeyboardConfirm
    }: {
        placeholder?: string;
        name?: string;
        label?: string;
        className?: string;
        contentClassName?: string;
        autoOpen?: boolean;
        autoFocus?: boolean;
        selectedItem?: ListItem;
        items: ListItem[];
        notFound?: Snippet<[{ inputValue: string }]>;
        onSelect?: (item: ListItem) => void;
        disabled?: boolean;
        isLoading?: boolean;
        onKeyboardConfirm?: (item: ListItem) => void;
    } = $props();

    let open = $state(untrack(() => autoOpen));
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
        const existingItem = items.find((i) => i.value.toLowerCase() === item.toLowerCase());

        if (existingItem) {
            handleOnSelect(existingItem);
        } else {
            const newItem = { value: item, label: item };
            items.push(newItem);
            handleOnSelect(newItem);
        }
    };

    const confirmWithKeyboard = (item: ListItem) => {
        selectedItem = item;
        onSelect?.(item);
        onKeyboardConfirm?.(item);
        closeAndFocusTrigger();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Enter' || !onKeyboardConfirm) {
            if (event.key === 'Enter' && !highlightedValue && inputValue) {
                createNewItem(inputValue);
                event.preventDefault();
                event.stopPropagation();
            } else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                event.stopPropagation();
            }
            return;
        }

        const highlightedItem = items.find((item) => item.value === highlightedValue);

        if (highlightedItem) {
            confirmWithKeyboard(highlightedItem);
        } else if (inputValue) {
            const existingItem = items.find(
                (item) => item.value.toLowerCase() === inputValue.toLowerCase()
            );
            const item = existingItem ?? { value: inputValue, label: inputValue };

            if (!existingItem) items.push(item);

            confirmWithKeyboard(item);
        } else {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
    };

    const handleOpenAutoFocus = (event: Event) => {
        if (!autoFocus) return;

        event.preventDefault();
        // Override the popover's default content focus to keep typing in the search input.
        inputRef.focus();
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger bind:ref={triggerRef}>
        {#snippet child({ props }: ChildProps)}
            <div class="flex w-full min-w-0 max-w-full items-center space-x-4">
                <Button
                    {...props}
                    variant="secondary"
                    {disabled}
                    class={cn('w-[200px] min-w-0 max-w-full justify-between', className)}
                    role="combobox"
                    aria-expanded={open}
                    data-testid="select-list-trigger"
                >
                    <span
                        class="min-w-0 flex-1 truncate text-left"
                        title={selectedItem?.label || label}
                    >
                        {selectedItem?.label || label}
                    </span>
                    <ChevronsUpDownIcon class="shrink-0 opacity-50" />
                </Button>
                {#if isLoading}
                    <Loader2Icon class="mr-2 h-4 w-4 shrink-0 animate-spin" />
                {/if}
            </div>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content
        class={cn('w-[200px] p-0', contentClassName)}
        onOpenAutoFocus={handleOpenAutoFocus}
    >
        <Command.Root bind:value={highlightedValue}>
            <Command.Input
                {placeholder}
                onkeydown={handleKeyDown}
                data-testid="select-list-input"
                bind:value={inputValue}
                bind:ref={inputRef}
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
                            <span class="min-w-0 flex-1 truncate" title={item.label}
                                >{item.label}</span
                            >
                        </Command.Item>
                    {/each}
                </Command.Group>
                {#if inputValue.trim()}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            onSelect={() => {
                                const newItem = { value: inputValue, label: inputValue };
                                items.push(newItem);
                                handleOnSelect(newItem);
                            }}
                            forceMount
                            keywords={[]}
                        >
                            <span class="opacity-50">Create:</span>
                            <span
                                class="ml-1 min-w-0 flex-1 truncate font-semibold"
                                title={inputValue}
                            >
                                {inputValue}
                            </span>
                        </Command.Item>
                    </div>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
