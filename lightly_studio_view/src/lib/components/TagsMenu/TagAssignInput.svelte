<script lang="ts">
    import { Input } from '$lib/components/ui/input/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import type { TagView } from '$lib/services/types';

    interface Props {
        options: TagView[];
        busy: boolean;
        showSelectionHint?: boolean;
        onSelect: (name: string) => void;
    }

    let { options, busy, showSelectionHint = false, onSelect }: Props = $props();

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
        if (busy) {
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

<div class="relative pt-2">
    <Tooltip
        content={showSelectionHint
            ? 'Select items in the grid, then assign or create a tag here.'
            : ''}
        position="right"
        triggerClass="block w-full"
    >
        <div class="w-full">
            <Input
                type="text"
                placeholder="Assign tag to selection"
                bind:value={searchQuery}
                onkeydown={handleKeydown}
                oninput={handleInput}
                onfocus={handleFocus}
                onblur={handleBlur}
                class="h-8 text-xs disabled:opacity-60"
                disabled={busy}
            />
        </div>
    </Tooltip>
    {#if showDropdown && (filteredOptions.length > 0 || (trimmedSearchQuery && !hasExactMatch))}
        <div
            class="absolute left-0 top-full z-50 mt-1 max-h-44 w-full overflow-auto rounded-md border bg-popover shadow-md"
        >
            {#each filteredOptions as tag (tag.tag_id)}
                <button
                    type="button"
                    class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent disabled:pointer-events-none disabled:opacity-60"
                    disabled={busy}
                    value={tag.name}
                    onclick={handleOptionClick}
                >
                    {tag.name}
                </button>
            {/each}
            {#if trimmedSearchQuery && !hasExactMatch}
                <button
                    type="button"
                    class="flex w-full items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent disabled:pointer-events-none disabled:opacity-60"
                    disabled={busy}
                    onclick={handleCreateClick}
                >
                    Create "{trimmedSearchQuery}"
                </button>
            {/if}
        </div>
    {/if}
</div>
