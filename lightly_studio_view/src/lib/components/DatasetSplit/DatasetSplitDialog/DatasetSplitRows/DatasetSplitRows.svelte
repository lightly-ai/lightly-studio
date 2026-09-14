<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { getSplitCounts } from '../../splitPreview';
    import DatasetSplitRow from '../DatasetSplitRow/DatasetSplitRow.svelte';

    interface Props {
        splits: Parameters<typeof getSplitCounts>[1];
        counts: number[];
        sampleCount: number;
    }

    let { splits = $bindable(), counts, sampleCount }: Props = $props();
</script>

<div class="space-y-3">
    {#each splits as split, index (split)}
        <DatasetSplitRow
            bind:split={splits[index]}
            {index}
            count={counts[index]}
            canRemove={splits.length > 2}
            onRemove={() => (splits = splits.filter((_, rowIndex) => rowIndex !== index))}
        />
    {/each}
    <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={splits.length >= sampleCount}
        onclick={() => (splits = [...splits, { tag_name: '', relative_size: 1 }])}
    >
        <Plus /> Add split
    </Button>
</div>
