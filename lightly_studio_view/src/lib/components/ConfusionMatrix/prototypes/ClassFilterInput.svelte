<script lang="ts">
    import { Input } from '$lib/components/ui/input/index.js';
    import { cn } from '$lib/utils';

    interface Props {
        classes: string[];
        query: string;
        maxSuggestions?: number;
    }

    let { classes, query = $bindable(), maxSuggestions = 8 }: Props = $props();

    let focused = $state(false);
    let highlightedIndex = $state(0);

    const parts = $derived(query.split(','));
    const completedTerms = $derived(
        new Set(
            parts
                .slice(0, -1)
                .map((part) => part.trim().toLowerCase())
                .filter((part) => part.length > 0)
        )
    );
    const lastTerm = $derived(parts[parts.length - 1].trim().toLowerCase());
    const suggestions = $derived(
        lastTerm
            ? classes
                  .filter((label) => {
                      const lower = label.toLowerCase();
                      return (
                          lower.includes(lastTerm) &&
                          lower !== lastTerm &&
                          !completedTerms.has(lower)
                      );
                  })
                  .slice(0, maxSuggestions)
            : []
    );
    const open = $derived(focused && suggestions.length > 0);

    $effect(() => {
        void query;
        highlightedIndex = 0;
    });

    // Replaces the partial last term with the picked label, ready for the next term.
    const applySuggestion = (label: string) => {
        const completed = parts
            .slice(0, -1)
            .map((part) => part.trim())
            .filter((part) => part.length > 0);
        query = [...completed, label].join(', ') + ', ';
    };

    const handleKeydown = (event: KeyboardEvent) => {
        if (!open) return;
        if (event.key === 'ArrowDown') {
            highlightedIndex = (highlightedIndex + 1) % suggestions.length;
            event.preventDefault();
        } else if (event.key === 'ArrowUp') {
            highlightedIndex = (highlightedIndex - 1 + suggestions.length) % suggestions.length;
            event.preventDefault();
        } else if (event.key === 'Enter') {
            applySuggestion(suggestions[highlightedIndex]);
            event.preventDefault();
        } else if (event.key === 'Escape') {
            focused = false;
        }
    };
</script>

<div class="relative max-w-[320px] flex-1">
    <Input
        bind:value={query}
        placeholder="Filter classes, e.g. car, truck, bus"
        class="h-8"
        role="combobox"
        aria-expanded={open}
        onfocus={() => (focused = true)}
        onblur={() => (focused = false)}
        onkeydown={handleKeydown}
        data-testid="confusion-matrix-class-filter"
    />
    {#if open}
        <ul
            class="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
            role="listbox"
            data-testid="class-filter-suggestions"
        >
            {#each suggestions as label, index (label)}
                <li role="option" aria-selected={index === highlightedIndex}>
                    <button
                        type="button"
                        class={cn(
                            'w-full truncate rounded-sm px-2 py-1.5 text-left text-sm',
                            index === highlightedIndex && 'bg-accent text-accent-foreground'
                        )}
                        onmousedown={(event) => event.preventDefault()}
                        onclick={() => applySuggestion(label)}
                        onmouseenter={() => (highlightedIndex = index)}
                    >
                        {label}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>
