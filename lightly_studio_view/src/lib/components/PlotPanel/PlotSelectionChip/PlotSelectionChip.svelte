<script lang="ts">
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components/ui/button';

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
        Plot filter: {count}
        {count === 1 ? itemLabel : `${itemLabel}s`}
    </span>
    <Button
        variant="ghost"
        size="icon"
        class="size-4 shrink-0 text-muted-foreground hover:bg-transparent hover:text-foreground"
        onclick={onClear}
        title="Clear plot filter (Esc)"
        aria-label="Clear plot filter"
    >
        <X />
    </Button>
</div>
