<script lang="ts">
    // Stub of the workflow status filter, so tests can see where the layout shows it.
    let { collectionId }: { collectionId: string } = $props();
</script>

<div data-testid="workflow-status-filter" data-collection-id={collectionId}></div>
