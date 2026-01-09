<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import Button from '$lib/components/ui/button/button.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SampleDetailsSidePanelAnnotation from '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { toast } from 'svelte-sonner';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';

    type SampleDetailsAnnotationSegmentProps = {
        annotationType: string | null;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        selectedAnnotationId: string | null;
        annotationsIdsToHide: Set<string>;
        collectionId: string;
        annotations: AnnotationView[];
        isPanModeEnabled: boolean;
        refetch: () => void;
    };

    let {
        annotationType = $bindable<string | null>(),
        addAnnotationEnabled = $bindable<boolean>(),
        addAnnotationLabel = $bindable<ListItem | undefined>(),
        selectedAnnotationId = $bindable<string | null>(),
        annotationsIdsToHide = $bindable<Set<string>>(),
        collectionId,
        annotations,
        isPanModeEnabled,
        refetch
    }: SampleDetailsAnnotationSegmentProps = $props();

    const { updateLastAnnotationType, isEditingMode, addReversibleAction } = useGlobalStorage();

    const annotationLabels = useAnnotationLabels({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const items = $derived(getSelectionItems($annotationLabels.data || []));

    const annotationsSort = $derived.by(() => {
        return annotations
            ? [...annotations].sort((a, b) =>
                  a.annotation_label.annotation_label_name.localeCompare(
                      b.annotation_label?.annotation_label_name
                  )
              )
            : [];
    });

    const annotationTypeItems = [
        {
            value: AnnotationType.OBJECT_DETECTION,
            label: 'Object detection'
        },
        {
            value: AnnotationType.INSTANCE_SEGMENTATION,
            label: 'Instance segmentation'
        }
    ];

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        if (selectedAnnotationId === annotationId) {
            selectedAnnotationId = null;
        } else {
            selectedAnnotationId = annotationId;
        }
    };

    const handleDeleteAnnotation = async (annotationId: string) => {
        if (!$annotationLabels.data) return;

        const annotation = annotations?.find((a) => a.sample_id === annotationId);
        if (!annotation) return;

        const _delete = async () => {
            try {
                addAnnotationDeleteToUndoStack({
                    annotation,
                    labels: $annotationLabels.data!,
                    addReversibleAction,
                    createAnnotation,
                    refetch
                });

                await deleteAnnotation(annotationId);
                toast.success('Annotation deleted successfully');
                refetch();
                if (selectedAnnotationId === annotationId) {
                    selectedAnnotationId = null;
                }
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
        };
        _delete();
    };

    const onToggleShowAnnotation = (annotationId: string) => {
        annotationsIdsToHide = new Set(
            annotationsIdsToHide.has(annotationId)
                ? [...annotationsIdsToHide].filter((id) => id !== annotationId)
                : [...annotationsIdsToHide, annotationId]
        );
    };
</script>

<Segment title="Annotations">
    <div class="flex flex-col gap-3 space-y-4">
        {#if $isEditingMode}
            <div class="items-left mb-2 flex flex-col justify-between space-y-2 bg-muted p-2">
                <div class="mb-2 w-full">
                    <Button
                        title="Add annotation"
                        variant={addAnnotationEnabled ? 'default' : 'outline'}
                        data-testid="create-rectangle"
                        class="w-full"
                        onclick={() => {
                            addAnnotationEnabled = !addAnnotationEnabled;
                        }}
                    >
                        Add annotation
                    </Button>
                </div>
                {#if addAnnotationEnabled}
                    <label class="flex w-full flex-col gap-3 text-muted-foreground">
                        <div class="text-sm">Select or create a label for a new annotation.</div>
                        <SelectList
                            {items}
                            selectedItem={items.find((i) => i.value === addAnnotationLabel?.value)}
                            name="annotation-label"
                            label="Choose or create a label"
                            className="w-full"
                            contentClassName="w-full"
                            placeholder="Select or create a label"
                            onSelect={(item) => {
                                addAnnotationLabel = item;
                            }}
                        >
                            {#snippet notFound({ inputValue })}
                                <LabelNotFound label={inputValue} />
                            {/snippet}
                        </SelectList>
                    </label>
                {/if}
            </div>
        {/if}
        <div class="flex flex-col gap-2">
            {#each annotationsSort as annotation}
                <SampleDetailsSidePanelAnnotation
                    {annotation}
                    isSelected={selectedAnnotationId === annotation.sample_id}
                    onClick={() => toggleAnnotationSelection(annotation.sample_id)}
                    onDeleteAnnotation={() => handleDeleteAnnotation(annotation.sample_id)}
                    isHidden={annotationsIdsToHide.has(annotation.sample_id)}
                    onToggleShowAnnotation={(e) => {
                        e.stopPropagation();
                        onToggleShowAnnotation(annotation.sample_id);
                    }}
                    onUpdate={refetch}
                    {collectionId}
                />
            {/each}
        </div>
    </div>
</Segment>
