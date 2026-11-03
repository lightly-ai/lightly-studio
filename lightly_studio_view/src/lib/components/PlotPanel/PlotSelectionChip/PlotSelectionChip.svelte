<script lang="ts">
    import { X } from '@lucide/svelte';

    interface Props {
        count: number;
        itemLabel: string;
        onClear: () => void;
    }

    let { count, itemLabel, onClear }: Props = $props();
</script>

<!-- Styled like the sidebar FilterChip so both clear actions look the same. -->
<div
    class="pointer-events-auto flex items-center gap-2 rounded-md border border-[#3c3c3c] bg-muted px-2 py-1.5"
    data-testid="plot-selection-chip"
>
    <span class="text-sm font-medium">
        {count}
        {count === 1 ? itemLabel : `${itemLabel}s`} selected
    </span>
    <button
        type="button"
        class="shrink-0 text-muted-foreground hover:text-foreground"
        onclick={onClear}
        title="Clear selection"
        aria-label="Clear selection"
    >
        <X class="size-4" />
    </button>
</div>
