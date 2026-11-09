<script lang="ts">
    interface Props {
        collectionId: string;
        sourceId?: string;
        flat?: boolean;
    }

    let { collectionId, sourceId, flat = false }: Props = $props();
</script>

<div
    data-testid="annotation-tree-stub"
    data-collection-id={collectionId}
    data-source-id={sourceId}
    data-flat={flat}
></div>
