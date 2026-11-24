<script lang="ts">
    import type { SlotProps } from '$lib/extensions';

    const { datasetId, collectionId }: SlotProps['dataset.toolbar'] = $props();
</script>

<span data-testid="registered">{datasetId}/{collectionId}</span>
