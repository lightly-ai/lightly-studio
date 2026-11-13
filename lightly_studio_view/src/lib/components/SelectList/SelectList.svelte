<script lang="ts">
    import CheckIcon from '@lucide/svelte/icons/check';
    import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
    import Loader2Icon from '@lucide/svelte/icons/loader-circle';
    import { tick, untrack, type Snippet } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components';
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
        onKeyboardConfirm,
        onCreate,
        allowCreate = true,
        labelledBy
    }: {
        placeholder?: string;
        name?: string;
        label?: string;
        labelledBy?: string;
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
        // Called when the user creates an item from the typed text, before onSelect.
        onCreate?: (item: ListItem) => void;
        // When false, users can only pick existing items.
        allowCreate?: boolean;
    } = $props();

    // Part of the trigger's accessible name, so it reads as "<field label> <selected value>".
    const valueId = $props.id();

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

    // Returns the item that matches the text, ignoring case, or creates a new one.
    // Returns undefined when there is no match and creating is not allowed.
    const getOrCreateItem = (text: string): ListItem | undefined => {
        const existingItem = items.find((i) => i.value.toLowerCase() === text.toLowerCase());
        if (existingItem) return existingItem;
        if (!allowCreate) return undefined;

        const newItem = { value: text, label: text };
        items.push(newItem);
        onCreate?.(newItem);
        return newItem;
    };

    const confirmWithKeyboard = (item: ListItem) => {
        selectedItem = item;
        onSelect?.(item);
        onKeyboardConfirm?.(item);
        closeAndFocusTrigger();
    };

    const getTypedItem = (): ListItem | undefined =>
        inputValue.trim() ? getOrCreateItem(inputValue) : undefined;

    // With onKeyboardConfirm, Enter confirms the highlighted or typed item. Without it,
    // Enter on a highlighted item is left to the command list.
    const getEnterItem = (): ListItem | undefined => {
        if (onKeyboardConfirm) {
            return items.find((item) => item.value === highlightedValue) ?? getTypedItem();
        }
        return highlightedValue ? undefined : getTypedItem();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.stopPropagation();
            return;
        }
        if (event.key !== 'Enter') return;

        const item = getEnterItem();
        if (!item) return;
        if (onKeyboardConfirm) {
            confirmWithKeyboard(item);
        } else {
            handleOnSelect(item);
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
                    variant="secondary"
                    buttonProps={{
                        ...props,
                        disabled,
                        class: cn('w-[200px] min-w-0 max-w-full justify-between', className),
                        role: 'combobox',
                        'aria-expanded': open,
                        ...(labelledBy ? { 'aria-labelledby': `${labelledBy} ${valueId}` } : {}),
                        'data-testid': 'select-list-trigger'
                    }}
                >
                    <span
                        id={valueId}
                        class="min-w-0 flex-1 truncate text-left"
                        title={selectedItem?.label ?? label}
                    >
                        {selectedItem?.label ?? label}
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
                {#if allowCreate && inputValue.trim()}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            onSelect={() => {
                                const item = getOrCreateItem(inputValue);
                                if (item) handleOnSelect(item);
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
