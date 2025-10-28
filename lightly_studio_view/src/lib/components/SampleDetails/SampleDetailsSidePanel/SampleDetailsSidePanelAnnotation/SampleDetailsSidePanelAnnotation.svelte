<script lang="ts">
    import { cn } from '$lib/utils';
    import { page } from '$app/state';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { Trash2, Eye, EyeOff } from '@lucide/svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import Button from '$lib/components/ui/button/button.svelte';

    const {
        annotation: annotationProp,
        isSelected = false,
        onClick,
        onUpdate,
        onToggleShowAnnotation,
        onDeleteAnnotation,
        isHidden = false,
        registerElement
    }: {
        annotation: AnnotationView;
        isSelected: boolean;
        onClick: () => void;
        onUpdate: () => void;
        onToggleShowAnnotation: (e: MouseEvent) => void;
        onDeleteAnnotation: (e: MouseEvent) => void;
        isHidden?: boolean;
        registerElement?: (annotationId: string, element: HTMLElement | null) => void;
    } = $props();

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
            annotation.object_detection_details || annotation.instance_segmentation_details;
        if (annotationWithDimensions) {
            const { width, height } = annotationWithDimensions;
            return `${Math.round(width)}x${Math.round(height)}px`;
        }
        return '';
    };
    const { isEditingMode } = page.data.globalStorage;
    const { datasetId } = page.data;
    const result = useAnnotationLabels();
    const items = $derived(getSelectionItems($result.data || []));

    const annotationId = $derived(annotationProp.annotation_id);

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            datasetId,
            annotationId,
            onUpdate
        })
    );

    const annotation = $derived($annotationResp.data || annotationProp);

    const value = $derived.by(() => {
        const currentValue = annotation.annotation_label.annotation_label_name;
        const item = items.find((i) => i.value === currentValue);
        return item ? item : { value: currentValue, label: currentValue };
    });

    let showDeleteConfirmation = $state(false);

    // Store reference to button element and register it with parent
    let buttonElement: HTMLButtonElement | null = $state(null);

    // Register element when it's bound or when annotation ID changes
    $effect(() => {
        if (registerElement) {
            registerElement(annotation.annotation_id, buttonElement);
        }

        // Cleanup when component unmounts
        return () => {
            if (registerElement) {
                registerElement(annotation.annotation_id, null);
            }
        };
    });
</script>

<button
    bind:this={buttonElement}
    type="button"
    class={cn(
        'flex w-full items-start justify-between gap-2 rounded-sm px-4 py-3 text-left align-baseline transition-colors',
        isSelected ? 'border border-accent-foreground/20 bg-accent' : 'bg-card hover:bg-accent/50'
    )}
    data-annotation-id={annotation.annotation_id}
    onclick={onClick}
>
    <span class="flex flex-1 flex-col gap-1">
        <span class="text-sm font-medium" data-testid="sample-details-pannel-annotation-name">
            {#if $isEditingMode}
                <SelectList
                    {items}
                    selectedItem={items.find((i) => i.value === value?.value)}
                    name="annotation-label"
                    placeholder="Select or create a label"
                    onSelect={(item) => {
                        updateAnnotation({
                            annotation_id: annotationId,
                            dataset_id: datasetId,
                            label_name: item.value
                        });
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
        <span class="text-xs text-muted-foreground">
            {formatAnnotationType(annotation.annotation_type)}
            {#if getAnnotationDimensions(annotation)}
                ({getAnnotationDimensions(annotation)})
            {/if}
        </span>
    </span>
    <div class="flex gap-3">
        {#if isHidden}
            <EyeOff class="size-6 text-muted-foreground" onclick={onToggleShowAnnotation} />
        {:else}
            <Eye class="size-6" onclick={onToggleShowAnnotation} />
        {/if}

        {#if $isEditingMode}
            <Popover.Root bind:open={showDeleteConfirmation}>
                <Popover.Trigger>
                    <Trash2 class="size-6" />
                </Popover.Trigger>
                <Popover.Content>
                    You are going to delete this annotation. This action cannot be undone.
                    <div class="mt-2 flex justify-end gap-2">
                        <Button
                            variant="destructive"
                            size="sm"
                            onclick={(e: MouseEvent) => {
                                e.stopPropagation();
                                onDeleteAnnotation(e);
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
</button>
