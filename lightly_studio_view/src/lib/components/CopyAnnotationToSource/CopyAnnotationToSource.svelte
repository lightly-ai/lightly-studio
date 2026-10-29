<script lang="ts">
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import { CopyPlus } from '@lucide/svelte';
    import { useCopyAnnotationToSource } from './useCopyAnnotationToSource.svelte';

    type Props = ReturnType<Parameters<typeof useCopyAnnotationToSource>[0]>;
    const { collectionId, annotation, onCopied }: Props = $props();
    const { copy, pending } = useCopyAnnotationToSource(() => ({
        collectionId,
        annotation,
        onCopied
    }));
</script>

<AnnotationSourcePicker
    {collectionId}
    excludeSourceId={annotation.annotation_collection_id}
    label="Duplicate to another annotation source"
    heading="Duplicate to"
    icon={CopyPlus}
    disabled={$pending}
    onPick={copy}
/>
