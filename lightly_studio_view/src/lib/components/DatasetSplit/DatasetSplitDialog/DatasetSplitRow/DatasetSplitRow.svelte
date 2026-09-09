<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { getSplitCounts } from '../../splitPreview';

    interface Props {
        split: Parameters<typeof getSplitCounts>[1][number];
        index: number;
        count?: number;
    }

    let { split = $bindable(), index, count }: Props = $props();
</script>

<div class="grid grid-cols-3 items-end gap-3 text-sm">
    <label class="space-y-1">
        Tag {index + 1}
        <Input bind:value={split.tag_name} />
    </label>
    <label class="space-y-1">
        Weight {index + 1}
        <Input type="number" min={1} step={1} bind:value={split.relative_size} />
    </label>
    <p aria-label={`Split ${index + 1} sample count`}>{count ?? '—'} samples</p>
</div>
