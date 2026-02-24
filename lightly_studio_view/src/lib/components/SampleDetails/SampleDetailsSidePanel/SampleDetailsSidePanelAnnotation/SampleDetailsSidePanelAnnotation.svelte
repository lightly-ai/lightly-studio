<script lang="ts">
    import { cn } from '$lib/utils';
    import { page } from '$app/state';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { Trash2, Eye, EyeOff, Lock, Unlock } from '@lucide/svelte';
    import { type AnnotationView } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import DeleteAnnotationPopUp from '$lib/components/DeleteAnnotationPopUp/DeleteAnnotationPopUp.svelte';

    const {
        annotation: annotationProp,
        isSelected = false,
        onClick,
        onUpdate,
        onToggleShowAnnotation,
        onDeleteAnnotation,
        isHidden = false,
        onChangeAnnotationLabel,
        canHighlight = false,
        onClickSelectList,
        onDelete,
        isLocked = false,
        onToggleLock
    }: {
        annotation: AnnotationView;
        isSelected: boolean;
        onClick: () => void;
        onUpdate: () => void;
        onToggleShowAnnotation: (e: MouseEvent) => void;
        onDeleteAnnotation: (e: MouseEvent) => void;
        onChangeAnnotationLabel?: (newLabel: string) => void | null | undefined;
        isHidden?: boolean;
        canHighlight?: boolean;
        onClickSelectList?: () => void;
        onDelete?: () => void;
        isLocked?: boolean;
        onToggleLock?: (e: MouseEvent) => void;
    } = $props();

    $effect(() => {
        if (showDeleteConfirmation) {
            return onDelete?.();
        }
    });

    const formatAnnotationType = (annotationType: string) => {
        switch (annotationType) {
            case 'object_detection':
                return 'Object Detection';
            case 'instance_segmentation':
                return 'Instance Segmentation';
            case 'semantic_segmentation':
                return 'Semantic Segmentation';
            case 'classification':
                return 'Image Classification';
            default:
                return annotationType;
        }
    };

    const getAnnotationDimensions = (annotation: AnnotationView) => {
        const annotationWithDimensions =
            annotation.object_detection_details || annotation.segmentation_details;
        if (annotationWithDimensions) {
            const { width, height } = annotationWithDimensions;
            return `${Math.round(width)}x${Math.round(height)}px`;
        }
        return '';
    };

    const { isEditingMode } = page.data.globalStorage;
    const collectionId = $derived(page.params.collection_id!);
    const result = $derived(useAnnotationLabels({ collectionId }));
    const items = $derived(getSelectionItems($result.data || []));
    const { addReversibleAction } = useGlobalStorage();

    const annotationId = $derived(annotationProp.sample_id);

    const {
        annotation: annotationResp,
        updateAnnotation,
        refetch
    } = $derived(
        useAnnotation({
            collectionId,
            annotationId,
            onUpdate
        })
    );

    const { updateAnnotations: updateAnnotationsRaw } = $derived(
        useUpdateAnnotationsMutation({
            collectionId
        })
    );

    const annotation = $derived($annotationResp.data || annotationProp);

    const value = $derived.by(() => {
        const currentValue = annotation.annotation_label.annotation_label_name;
        const item = items.find((i) => i.value === currentValue);
        return item ? item : { value: currentValue, label: currentValue };
    });

    let showDeleteConfirmation = $state(false);
</script>

<div
    class={cn(
        'gap-2 rounded-sm px-4 py-3 text-left align-baseline transition-colors',
        isSelected ? 'border border-accent-foreground/20 bg-accent' : 'bg-card hover:bg-accent/50',
        canHighlight ? 'border border-primary' : ''
    )}
>
    <button
        type="button"
        class="flex w-full items-start justify-between text-left"
        data-annotation-id={annotation.sample_id}
        onclick={onClick}
    >
        <span class="flex flex-1 flex-col gap-1">
            <span class="text-sm font-medium" data-testid="sample-details-pannel-annotation-name">
                {#if $isEditingMode}
                    <div
                        role="button"
                        tabindex="0"
                        onkeydown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                onClickSelectList?.();
                            }
                        }}
                        onclick={(e) => {
                            if (!onClickSelectList) return;
                            e.stopPropagation();
                            onClickSelectList();
                        }}
                    >
                        <SelectList
                            {items}
                            selectedItem={items.find((i) => i.value === value?.value)}
                            name="annotation-label"
                            placeholder="Select or create a label"
                            onSelect={async (item) => {
                                addAnnotationLabelChangeToUndoStack({
                                    annotations: [
                                        {
                                            sample_id: annotationId,
                                            annotation_label: {
                                                annotation_label_name:
                                                    annotation.annotation_label
                                                        .annotation_label_name
                                            }
                                        }
                                    ],
                                    collectionId,
                                    addReversibleAction,
                                    updateAnnotations: updateAnnotationsRaw,
                                    refresh: refetch
                                });
                                await updateAnnotation({
                                    annotation_id: annotationId,
                                    collection_id: collectionId,
                                    label_name: item.value
                                });
                                onChangeAnnotationLabel?.(item.value);
                            }}
                        >
                            {#snippet notFound({ inputValue })}
                                <LabelNotFound label={inputValue} />
                            {/snippet}
                        </SelectList>
                    </div>
                {:else}
                    {annotation.annotation_label.annotation_label_name}
                {/if}
            </span>
            <span class="text-xs text-muted-foreground">
                {formatAnnotationType(annotation.annotation_type)}
                {#if getAnnotationDimensions(annotation)}
                    ({getAnnotationDimensions(annotation)})
                {/if}
            </span>
        </span>
        <div class="flex gap-3 pl-1">
            {#if $isEditingMode && annotation.annotation_type != 'object_detection'}
                {#if isLocked}
                    <Lock
                        class="size-6 text-muted-foreground"
                        onclick={(e) => {
                            e.stopPropagation();
                            onToggleLock?.(e);
                        }}
                    />
                {:else}
                    <Unlock
                        class="size-6"
                        onclick={(e) => {
                            e.stopPropagation();
                            onToggleLock?.(e);
                        }}
                    />
                {/if}
            {/if}
            {#if isHidden}
                <EyeOff class="size-6 text-muted-foreground" onclick={onToggleShowAnnotation} />
            {:else}
                <Eye class="size-6" onclick={onToggleShowAnnotation} />
            {/if}

            {#if $isEditingMode}
                <DeleteAnnotationPopUp onDelete={onDeleteAnnotation}>
                    <Trash2 class="size-6" />
                </DeleteAnnotationPopUp>
            {/if}
        </div>
    </button>
</div>
