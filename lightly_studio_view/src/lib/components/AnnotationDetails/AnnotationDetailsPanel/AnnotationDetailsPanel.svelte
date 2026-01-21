<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import { useRemoveTagFromAnnotation } from '$lib/hooks/useRemoveTagFromAnnotation/useRemoveTagFromAnnotation';
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
        sampleDetails,
        collectionId
    }: {
        annotation: AnnotationView;
        onUpdate: () => void;
        sampleDetails: Snippet;
        collectionId: string;
    } = $props();
    const { removeTagFromAnnotation } = useRemoveTagFromAnnotation();

    const tags = $derived(annotation.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromAnnotation(annotation.sample_id, tagId);
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
        } catch (error) {
            toast.error('Failed to delete annotation. Please try again.');
            console.error('Error deleting annotation:', error);
        }
    };

    const datasetId = $derived(page.params.dataset_id ?? page.data.datasetId);
    const collectionType = $derived(page.params.collection_type ?? page.data.collectionType);

    const { gotoNextAnnotation } = $derived.by(() =>
        useAnnotationDeleteNavigation({
            collectionId,
            datasetId,
            collectionType,
            annotationIndex: page.data.annotationIndex,
            annotationAdjacents: page.data.annotationAdjacents
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

            {@render sampleDetails()}

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
