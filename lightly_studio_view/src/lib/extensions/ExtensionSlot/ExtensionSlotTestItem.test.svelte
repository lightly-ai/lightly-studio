<script lang="ts">
    const { datasetId, collectionId }: { datasetId: string; collectionId: string } = $props();
</script>

<span data-testid="registered">{datasetId}/{collectionId}</span>
