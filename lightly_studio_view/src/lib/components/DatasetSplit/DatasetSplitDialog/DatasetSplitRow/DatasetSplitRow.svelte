<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { getSplitCounts } from '../../splitPreview';

    interface Props {
        split: Parameters<typeof getSplitCounts>[1][number];
        index: number;
        count?: number;
        canRemove: boolean;
        onRemove: () => void;
    }

    let { split = $bindable(), index, count, canRemove, onRemove }: Props = $props();
</script>

<div class="grid grid-cols-[minmax(0,1fr)_5rem_6rem_auto] items-end gap-3 text-sm">
    <label class="space-y-1">
        Tag {index + 1}
        <Input bind:value={split.tag_name} />
    </label>
    <label class="space-y-1">
        Weight {index + 1}
        <Input type="number" min={1} step={1} bind:value={split.relative_size} />
    </label>
    <p
        class="flex h-10 items-center justify-end tabular-nums text-muted-foreground"
        aria-label={`Split ${index + 1} sample count`}
    >
        {count ?? '—'}
        {count === 1 ? 'sample' : 'samples'}
    </p>
    <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={`Remove split ${index + 1}`}
        disabled={!canRemove}
        onclick={onRemove}
    >
        <X />
    </Button>
</div>
