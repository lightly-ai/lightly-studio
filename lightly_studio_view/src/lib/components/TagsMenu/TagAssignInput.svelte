<script lang="ts">
    import { Input } from '$lib/components/ui/input/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import type { TagView } from '$lib/services/types';
    import { Button } from '$lib/components';

    interface Props {
        options: TagView[];
        hasSelection: boolean;
        busy: boolean;
        onSelect: (name: string) => void;
    }

    let { options, hasSelection, busy, onSelect }: Props = $props();
    const showSelectionHint = $derived(!hasSelection);

    let searchQuery = $state('');
    let showDropdown = $state(false);
    const trimmedSearchQuery = $derived(searchQuery.trim());
    const normalizedSearchQuery = $derived(trimmedSearchQuery.toLowerCase());

    const filteredOptions = $derived<TagView[]>(
        trimmedSearchQuery
            ? options.filter((t) => t.name.toLowerCase().includes(normalizedSearchQuery))
            : options
    );

    const hasExactMatch = $derived(
        options.some((t) => t.name.toLowerCase() === normalizedSearchQuery)
    );

    function handleSelect(name: string) {
        if (busy || !hasSelection) {
            return;
        }
        onSelect(name);
        searchQuery = '';
        showDropdown = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const exactMatch = options.find((t) => t.name.toLowerCase() === normalizedSearchQuery);
            if (exactMatch) {
                handleSelect(exactMatch.name);
            } else if (trimmedSearchQuery) {
                handleSelect(trimmedSearchQuery);
            }
        }
        if (event.key === 'Escape') {
            searchQuery = '';
            showDropdown = false;
        }
    }

    function handleInput() {
        showDropdown = true;
    }

    function handleFocus() {
        showDropdown = true;
    }

    function handleBlur() {
        setTimeout(() => (showDropdown = false), 100);
    }

    function handleOptionClick(event: MouseEvent) {
        const tagName = (event.currentTarget as HTMLButtonElement).value;
        handleSelect(tagName);
    }

    function handleCreateClick() {
        handleSelect(trimmedSearchQuery);
    }
</script>

{#snippet tagInput()}
    <div class="w-full">
        <Input
            type="text"
            placeholder="Assign tag to selection"
            bind:value={searchQuery}
            onkeydown={handleKeydown}
            oninput={handleInput}
            onfocus={handleFocus}
            onblur={handleBlur}
            isPending={busy}
            disabled={!hasSelection}
        />
    </div>
{/snippet}

<div class="relative pt-2">
    {#if showSelectionHint}
        <Tooltip
            content="Select items in the grid, then assign or create a tag here."
            position="right"
            triggerClass="block w-full"
        >
            {@render tagInput()}
        </Tooltip>
    {:else}
        {@render tagInput()}
    {/if}
    {#if showDropdown && (filteredOptions.length > 0 || (trimmedSearchQuery && !hasExactMatch))}
        <div
            class="absolute left-0 top-full z-50 mt-1 max-h-44 w-full overflow-auto rounded-md border bg-popover shadow-md"
        >
            {#each filteredOptions as tag (tag.tag_id)}
                <Button
                    isPending={busy}
                    buttonProps={{
                        type: 'button',
                        class: 'w-full justify-start px-2 py-1.5 text-xs font-normal',
                        disabled: busy || !hasSelection,
                        value: tag.name,
                        onclick: handleOptionClick
                    }}
                >
                    {tag.name}
                </Button>
            {/each}
            {#if trimmedSearchQuery && !hasExactMatch}
                <Button
                    isPending={busy}
                    buttonProps={{
                        type: 'button',
                        class: 'w-full justify-start gap-1 px-2 py-1.5 text-xs font-normal text-muted-foreground',
                        disabled: busy || !hasSelection,
                        onclick: handleCreateClick
                    }}
                >
                    Create "{trimmedSearchQuery}"
                </Button>
            {/if}
        </div>
    {/if}
</div>
