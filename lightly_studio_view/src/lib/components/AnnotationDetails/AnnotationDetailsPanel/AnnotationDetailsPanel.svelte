<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import SegmentTags from '../../SegmentTags/SegmentTags.svelte';
    import { type AnnotationView } from '$lib/api/lightly_studio_local';
    import type { Snippet } from 'svelte';
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { toast } from 'svelte-sonner';
    import { useAnnotationDeleteNavigation } from '$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation';
    import DeleteAnnotationPopUp from '$lib/components/DeleteAnnotationPopUp/DeleteAnnotationPopUp.svelte';

    const {
        annotation,
        onUpdate,
        children,
        collectionId
    }: {
        annotation: AnnotationView;
        onUpdate: () => void;
        children: Snippet;
        collectionId: string;
    } = $props();
    const { removeTagFromSample } = useRemoveTagFromSample({ collectionId });

    const tags = $derived(annotation.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromSample(annotation.sample_id, tagId);
        onUpdate();
    };

    const { isEditingMode } = page.data.globalStorage;

    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });

    const handleDeleteAnnotation = async () => {
        try {
            await deleteAnnotation(annotation.sample_id);

            toast.success('Annotation deleted successfully');

            gotoNextAnnotation();
        } catch {
            toast.error('Failed to delete annotation. Please try again.');
        }
    };

    const datasetId = $derived(page.params.dataset_id ?? page.data.datasetId);
    const collectionType = $derived(page.params.collection_type ?? page.data.collectionType);

    const { gotoNextAnnotation } = $derived.by(() =>
        useAnnotationDeleteNavigation({
            annotationId: annotation.sample_id,
            collectionId,
            datasetId,
            collectionType
        })
    );
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <AnnotationMetadata {annotation} {onUpdate} />

            {@render children()}

            {#if $isEditingMode}
                <DeleteAnnotationPopUp onDelete={handleDeleteAnnotation}>
                    <Button
                        variant="destructive"
                        class="w-full"
                        data-testid="delete-annotation-trigger">Delete annotation</Button
                    >
                </DeleteAnnotationPopUp>
            {/if}
        </div>
    </CardContent>
</Card>
