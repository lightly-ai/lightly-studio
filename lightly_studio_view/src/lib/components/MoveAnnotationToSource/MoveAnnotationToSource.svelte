<script lang="ts">
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import { useMoveAnnotationsToSource } from '$lib/hooks';
    import { FolderInput } from '@lucide/svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        annotation: { sample_id: string; annotation_collection_id: string };
        onMoved?: () => void;
    }
    const { collectionId, annotation, onMoved }: Props = $props();
    const { moveToSource, isPending } = useMoveAnnotationsToSource();

    async function move(sourceName: string) {
        const moved = await moveToSource({
            collectionId,
            annotationIds: [annotation.sample_id],
            sourceName
        });
        if (moved) onMoved?.();
        return moved;
    }
</script>

<AnnotationSourcePicker
    {collectionId}
    excludeSourceId={annotation.annotation_collection_id}
    label="Move to another annotation source"
    heading="Move to"
    icon={FolderInput}
    disabled={$isPending}
    onPick={move}
/>
