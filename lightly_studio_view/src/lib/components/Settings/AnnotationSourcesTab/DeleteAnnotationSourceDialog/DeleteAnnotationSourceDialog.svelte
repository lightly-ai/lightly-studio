<script lang="ts">
    import DeleteAnnotationSource from '$lib/components/AnnotationCollectionsMenu/DeleteAnnotationSource/DeleteAnnotationSource.svelte';

    interface Props {
        collectionId: string;
        source: { id: string; name: string; annotationCount: number } | null;
        onClose: () => void;
    }

    const { collectionId, source, onClose }: Props = $props();
</script>

{#if source}
    <DeleteAnnotationSource
        {collectionId}
        source={{ id: source.id, name: source.name }}
        annotationCount={source.annotationCount}
        {onClose}
    />
{/if}
