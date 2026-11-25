<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { onDestroy } from 'svelte';
    import { shouldShowBoundingBoxForAnnotation } from '$lib/utils/shouldShowBoundingBoxForAnnotation';

    const {
        annotation,
        collectionId,
        isResizable = false,
        onAnnotationUpdated,
        sample,
        toggleAnnotationSelection,
        highlight = 'auto',
        scale = 1,
        colorBySource,
        showSourceLabels = false
    }: {
        sampleId: string;
        collectionId: string;
        annotation: AnnotationView;
        isResizable?: boolean;
        onAnnotationUpdated?: () => void;
        sample: {
            width: number;
            height: number;
        };
        toggleAnnotationSelection: (annotationId: string) => void;
        highlight?: 'active' | 'disabled' | 'auto';
        scale: number;
        colorBySource?: boolean;
        showSourceLabels?: boolean;
    } = $props();
    const { addReversibleAction, maskOpacity } = useGlobalStorage();
    const { showAnnotationTextLabelsStore, showBoundingBoxesForSegmentationStore } = useSettings();

    // The image already carries its annotations, so only use the hook to save edits.
    // Fetching each annotation again costs one request per box when the view opens.
    const { updateAnnotation } = useAnnotation(() => ({
        collectionId,
        annotationId: annotation.sample_id,
        enabled: false
    }));
    const { setCurrentBoundingBox, setIsMovingAnnotation, setMovedAnnotation } =
        useAnnotationLabelContext();
    // The box is remounted after an edit, so a drag can't be left marked as running. Only the
    // instance that started the drag resets it.
    let isDragging = false;
    const setDragging = (value: boolean) => {
        isDragging = value;
        setIsMovingAnnotation(value);
    };
    onDestroy(() => isDragging && setIsMovingAnnotation(false));

    let selectionBox = $derived(getBoundingBox(annotation));
    const showBoundingBox = $derived(
        shouldShowBoundingBoxForAnnotation(annotation, $showBoundingBoxesForSegmentationStore)
    );

    const onBoundingBoxChanged = (bbox: BoundingBox) => {
        setCurrentBoundingBox(bbox);
        const previousAnnotation = annotation;
        setMovedAnnotation(previousAnnotation.sample_id, bbox);
        const _update = async () => {
            try {
                await updateAnnotation({
                    annotation_id: previousAnnotation.sample_id,
                    collection_id: collectionId,
                    bounding_box: bbox
                });
                onAnnotationUpdated?.();
                addAnnotationUpdateToUndoStack({
                    annotation: previousAnnotation,
                    collection_id: collectionId,
                    addReversibleAction,
                    updateAnnotation,
                    onUndo: () => onAnnotationUpdated?.()
                });
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
            }
        };
        _update();
    };
</script>

{#if selectionBox}
    {#key selectionBox}
        <SelectableSvgGroup
            groupId={annotation.sample_id}
            onSelect={toggleAnnotationSelection}
            box={selectionBox}
        >
            <SampleAnnotation
                {annotation}
                showLabel={$showAnnotationTextLabelsStore || showSourceLabels}
                {showBoundingBox}
                imageWidth={sample.width}
                constraintBox={{
                    x: 0,
                    y: 0,
                    width: sample.width,
                    height: sample.height
                }}
                {isResizable}
                {onBoundingBoxChanged}
                onDragStart={() => setDragging(true)}
                onDragStop={() => setDragging(false)}
                {highlight}
                {scale}
                {colorBySource}
                maskOpacity={$maskOpacity}
                isSelectable
            />
        </SelectableSvgGroup>
    {/key}
{/if}
