<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Button } from '$lib/components';
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
        variant="outline"
        icon={Plus}
        disabledReason={splits.length >= sampleCount
            ? 'Cannot add more splits than the number of samples.'
            : ''}
        buttonProps={{
            type: 'button',
            size: 'sm',
            onclick: () => (splits = [...splits, { tag_name: '', relative_size: 1 }])
        }}
    >
        Add split
    </Button>
</div>
