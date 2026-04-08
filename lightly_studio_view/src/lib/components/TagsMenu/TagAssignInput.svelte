<script lang="ts">
    import { Input } from '$lib/components/ui/input/index.js';
    import type { TagView } from '$lib/services/types';

    interface Props {
        options: TagView[];
        busy: boolean;
        onSelect: (name: string) => void;
    }

    let { options, busy, onSelect }: Props = $props();

    let searchQuery = $state('');
    let showDropdown = $state(false);

    const filteredOptions = $derived<TagView[]>(
        searchQuery.trim()
            ? options.filter((t) => t.name.toLowerCase().includes(searchQuery.toLowerCase()))
            : options
    );

    const hasExactMatch = $derived(
        options.some((t) => t.name.toLowerCase() === searchQuery.trim().toLowerCase())
    );

    function handleSelect(name: string) {
        onSelect(name);
        searchQuery = '';
        showDropdown = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            const exactMatch = options.find(
                (t) => t.name.toLowerCase() === searchQuery.trim().toLowerCase()
            );
            if (exactMatch) {
                handleSelect(exactMatch.name);
            } else if (searchQuery.trim()) {
                handleSelect(searchQuery.trim());
            }
        }
        if (event.key === 'Escape') {
            searchQuery = '';
            showDropdown = false;
        }
    }
</script>

<div class="relative pt-2">
    <Input
        type="text"
        placeholder="Assign tag to selection"
        bind:value={searchQuery}
        onkeydown={handleKeydown}
        oninput={() => (showDropdown = true)}
        onfocus={() => (showDropdown = true)}
        onblur={() => setTimeout(() => (showDropdown = false), 100)}
        class="h-8 text-xs disabled:opacity-60"
        disabled={busy}
    />
    {#if showDropdown && (filteredOptions.length > 0 || (searchQuery.trim() && !hasExactMatch))}
        <div
            class="absolute left-0 top-full z-50 mt-1 max-h-44 w-full overflow-auto rounded-md border bg-popover shadow-md"
        >
            {#each filteredOptions as tag (tag.tag_id)}
                <button
                    type="button"
                    class="flex w-full items-center px-2 py-1.5 text-xs hover:bg-accent"
                    onclick={() => handleSelect(tag.name)}
                >
                    {tag.name}
                </button>
            {/each}
            {#if searchQuery.trim() && !hasExactMatch}
                <button
                    type="button"
                    class="flex w-full items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                    onclick={() => handleSelect(searchQuery.trim())}
                >
                    Create "{searchQuery.trim()}"
                </button>
            {/if}
        </div>
    {/if}
</div>
