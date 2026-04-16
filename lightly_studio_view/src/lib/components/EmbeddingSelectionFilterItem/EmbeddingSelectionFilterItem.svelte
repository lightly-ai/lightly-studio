<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { X } from '@lucide/svelte';

    type Props = {
        checked: boolean;
        selectionCount: number;
        itemLabel: string;
        onVisibilityChange: (checked: boolean) => void;
        onClear: () => void;
    };

    let { checked, selectionCount, itemLabel, onVisibilityChange, onClear }: Props = $props();
</script>

<div
    class="rounded-md border border-amber-500/35 bg-amber-500/10 px-2 py-1.5"
    data-testid="embedding-selection-filter-chip"
>
    <div class="flex items-center gap-2">
        <Checkbox
            {checked}
            aria-label="Embedding plot filter"
            onCheckedChange={(nextChecked) => onVisibilityChange(nextChecked === true)}
        />
        <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-medium">Embedding Plot Filter</div>
            <div class="text-xs text-muted-foreground">
                {selectionCount}
                {selectionCount === 1 ? itemLabel : `${itemLabel}s`}
            </div>
        </div>
        <button
            class="text-muted-foreground hover:text-foreground"
            onclick={onClear}
            title="Clear embedding plot filter"
            aria-label="Clear embedding plot filter"
        >
            <X class="size-4" />
        </button>
    </div>
</div>
