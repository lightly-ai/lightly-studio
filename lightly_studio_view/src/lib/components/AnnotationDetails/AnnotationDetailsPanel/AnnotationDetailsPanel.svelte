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
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { toast } from 'svelte-sonner';
    import { useAnnotationDeleteNavigation } from '$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation';

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

    let showDeleteConfirmation = $state(false);
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
                <Popover.Root bind:open={showDeleteConfirmation}>
                    <Popover.Trigger>
                        <Button variant="destructive" class="w-full" data-testid="delete-annotation-trigger">
                            Delete annotation
                        </Button>
                    </Popover.Trigger>
                    <Popover.Content>
                        You are going to delete this annotation. This action cannot be undone.
                        <div class="mt-2 flex justify-end gap-2">
                            <Button
                                variant="destructive"
                                size="sm"
                                data-testid="confirm-delete-annotation"
                                onclick={(e: MouseEvent) => {
                                    e.stopPropagation();
                                    handleDeleteAnnotation();
                                    showDeleteConfirmation = false;
                                }}>Delete</Button
                            >
                            <Button
                                variant="outline"
                                size="sm"
                                onclick={(e: MouseEvent) => {
                                    e.stopPropagation();
                                    showDeleteConfirmation = false;
                                }}>Cancel</Button
                            >
                        </div>
                    </Popover.Content>
                </Popover.Root>
            {/if}
        </div>
    </CardContent>
</Card>
