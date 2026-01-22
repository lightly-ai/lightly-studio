<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { cn } from '$lib/utils';
    import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import { Trash2 } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import Button from '$lib/components/ui/button/button.svelte';

    type SampleDetailsClassificationSegmentProps = {
        collectionId: string;
        annotations: AnnotationView[];
        refetch: () => void;
        sampleId: string;
    };

    let { collectionId, annotations, refetch, sampleId }: SampleDetailsClassificationSegmentProps =
        $props();

    const { isEditingMode, addReversibleAction } = useGlobalStorage();

    const annotationLabels = useAnnotationLabels({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ collectionId });
    const { createLabel } = useCreateLabel({ collectionId });
    const { updateAnnotations } = useUpdateAnnotationsMutation({ collectionId });
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollection({ collectionId: datasetId })
    );

    const items = $derived(getSelectionItems($annotationLabels.data || []));

    const classificationAnnotations = $derived.by(() => {
        return annotations
            ? [...annotations]
                  .filter(
                      (annotation) => annotation.annotation_type === AnnotationType.CLASSIFICATION
                  )
                  .sort((a, b) =>
                      a.annotation_label.annotation_label_name.localeCompare(
                          b.annotation_label?.annotation_label_name
                      )
                  )
            : [];
    });

    const handleDeleteAnnotation = async (annotationId: string) => {
        if (!$annotationLabels.data) return;

        const annotation = annotations?.find((a) => a.sample_id === annotationId);
        if (!annotation) return;

        try {
            addAnnotationDeleteToUndoStack({
                annotation,
                labels: $annotationLabels.data!,
                addReversibleAction,
                createAnnotation,
                refetch
            });

            await deleteAnnotation(annotationId);
            toast.success('Classification deleted successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to delete classification. Please try again.');
            console.error('Error deleting classification:', error);
        }
    };

    const createClassificationAnnotation = async (labelName: string) => {
        if (!$annotationLabels.data) return false;

        let label = $annotationLabels.data.find(
            (labelItem) => labelItem.annotation_label_name === labelName
        );

        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: labelName
            });
        }

        try {
            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: AnnotationType.CLASSIFICATION,
                annotation_label_id: label.annotation_label_id!
            });

            if (annotations.length === 0) {
                refetchRootCollection();
            }

            addAnnotationCreateToUndoStack({
                annotation: newAnnotation,
                addReversibleAction,
                deleteAnnotation,
                refetch
            });

            refetch();
            toast.success('Classification created successfully');
            return true;
        } catch (error) {
            toast.error('Failed to create classification. Please try again.');
            console.error('Error creating classification:', error);
            return false;
        }
    };

    const updateClassificationLabel = async (annotation: AnnotationView, labelName: string) => {
        addAnnotationLabelChangeToUndoStack({
            annotations: [
                {
                    sample_id: annotation.sample_id,
                    annotation_label: {
                        annotation_label_name: annotation.annotation_label.annotation_label_name
                    }
                }
            ],
            collectionId,
            addReversibleAction,
            updateAnnotations,
            refresh: refetch
        });

        try {
            await updateAnnotations([
                {
                    annotation_id: annotation.sample_id,
                    collection_id: collectionId,
                    label_name: labelName
                }
            ]);
            refetch();
        } catch (error) {
            toast.error('Failed to update classification label. Please try again.');
            console.error('Error updating classification label:', error);
        }
    };

    const getLabelValue = (annotation: AnnotationView) => {
        const currentValue = annotation.annotation_label.annotation_label_name;
        const item = items.find((i) => i.value === currentValue);
        return item ?? { value: currentValue, label: currentValue };
    };

    let draftCounter = 0;
    let draftClassifications = $state<string[]>([]);
    let deleteConfirmationId = $state<string | null>(null);

    const addDraftClassification = () => {
        draftCounter += 1;
        draftClassifications = [...draftClassifications, `draft-${Date.now()}-${draftCounter}`];
    };

    const removeDraftClassification = (draftId: string) => {
        draftClassifications = draftClassifications.filter((id) => id !== draftId);
    };

    $effect(() => {
        if (!sampleId) return;
        draftClassifications = [];
    });
</script>

<Segment title="Classification">
    <div class="flex flex-col gap-3 space-y-4">
        <div class="flex flex-col gap-2">
            {#each classificationAnnotations as annotation}
                <div
                    class="flex w-full items-center justify-between gap-2 rounded-sm bg-card px-4 py-3 text-left"
                    data-annotation-id={annotation.sample_id}
                >
                    <span class="flex flex-1 flex-col gap-1">
                        <span class="text-sm font-medium">
                            {#if $isEditingMode}
                                <SelectList
                                    {items}
                                    selectedItem={items.find(
                                        (i) => i.value === getLabelValue(annotation)?.value
                                    )}
                                    name="classification-label"
                                    placeholder="Select or create a label"
                                    className="w-full"
                                    onSelect={async (item) => {
                                        await updateClassificationLabel(annotation, item.value);
                                    }}
                                >
                                    {#snippet notFound({ inputValue })}
                                        <LabelNotFound label={inputValue} />
                                    {/snippet}
                                </SelectList>
                            {:else}
                                {annotation.annotation_label.annotation_label_name}
                            {/if}
                        </span>
                    </span>
                    <div class="flex items-center gap-3">
                        {#if $isEditingMode}
                            <Popover.Root
                                open={deleteConfirmationId === annotation.sample_id}
                                onOpenChange={(open) => {
                                    deleteConfirmationId = open ? annotation.sample_id : null;
                                }}
                            >
                                <Popover.Trigger>
                                    <Trash2 class="size-6" />
                                </Popover.Trigger>
                                <Popover.Content>
                                    You are going to delete this classification. This action cannot
                                    be undone.
                                    <div class="mt-2 flex justify-end gap-2">
                                        <Button
                                            variant="destructive"
                                            size="sm"
                                            onclick={(e: MouseEvent) => {
                                                e.stopPropagation();
                                                handleDeleteAnnotation(annotation.sample_id);
                                                deleteConfirmationId = null;
                                            }}
                                        >
                                            Delete
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onclick={(e: MouseEvent) => {
                                                e.stopPropagation();
                                                deleteConfirmationId = null;
                                            }}
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                </Popover.Content>
                            </Popover.Root>
                        {/if}
                    </div>
                </div>
            {/each}
            {#if $isEditingMode}
                {#each draftClassifications as draftId (draftId)}
                    <div
                        class={cn(
                            'flex w-full items-center justify-between gap-2 rounded-sm px-4 py-3 text-left',
                            'bg-card'
                        )}
                        data-annotation-id={draftId}
                    >
                        <span class="flex flex-1 flex-col gap-1">
                            <span class="text-sm font-medium">
                                <SelectList
                                    {items}
                                    name="classification-label"
                                    placeholder="Select or create a label"
                                    className="w-full"
                                    onSelect={async (item) => {
                                        const created = await createClassificationAnnotation(
                                            item.value
                                        );
                                        if (created) {
                                            removeDraftClassification(draftId);
                                        }
                                    }}
                                >
                                    {#snippet notFound({ inputValue })}
                                        <LabelNotFound label={inputValue} />
                                    {/snippet}
                                </SelectList>
                            </span>
                        </span>
                        <div class="flex items-center gap-3">
                            <Trash2
                                class="size-6 text-muted-foreground"
                                onclick={() => {
                                    removeDraftClassification(draftId);
                                }}
                            />
                        </div>
                    </div>
                {/each}
                <button
                    type="button"
                    class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                    onclick={addDraftClassification}
                    data-testid="add-classification-button"
                >
                    +
                </button>
            {/if}
        </div>
    </div>
</Segment>
