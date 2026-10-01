<script lang="ts">
    import DatasetSplitDialog from '../DatasetSplitDialog/DatasetSplitDialog.svelte';
    import { useDatasetSplit } from '../useDatasetSplit/useDatasetSplit.svelte';

    interface Props {
        collectionId: string;
        sampleType: 'image' | 'video';
        onClose: () => void;
    }

    let { collectionId, sampleType, onClose }: Props = $props();
    const { sampleCount, tags, pending, error, submit } = useDatasetSplit(() => ({
        collectionId,
        sampleType,
        onClose: () => onClose()
    }));
</script>

<DatasetSplitDialog
    {sampleCount}
    existingTagNames={$tags.map((tag) => tag.name)}
    pending={$pending}
    error={$error}
    onSubmit={submit}
    {onClose}
/>
