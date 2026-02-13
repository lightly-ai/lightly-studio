<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    const {
        annotationId,
        collectionId,
        isResizable = false,
        onAnnotationUpdated,
        sample,
        toggleAnnotationSelection,
        highlight = 'auto',
        scale = 1
    }: {
        sampleId: string;
        collectionId: string;
        annotationId: string;
        isResizable?: boolean;
        onAnnotationUpdated?: () => void;
        sample: {
            width: number;
            height: number;
        };
        toggleAnnotationSelection: (annotationId: string) => void;
        highlight?: 'active' | 'disabled' | 'auto';
        scale: number;
    } = $props();
    const { addReversibleAction } = useGlobalStorage();
    const { showAnnotationTextLabelsStore } = useSettings();

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            collectionId,
            annotationId
        })
    );
    const { setCurrentBoundingBox } = useAnnotationLabelContext();

    let annotation = $derived($annotationResp.data);

    let selectionBox = $derived(annotation ? getBoundingBox(annotation!) : undefined);

    const onBoundingBoxChanged = (bbox: BoundingBox) => {
        setCurrentBoundingBox(bbox);
        const _update = async () => {
            try {
                await updateAnnotation({
                    annotation_id: annotationId,
                    collection_id: collectionId,
                    bounding_box: bbox
                });
                onAnnotationUpdated?.();
                if (annotation)
                    addAnnotationUpdateToUndoStack({
                        annotation,
                        collection_id: collectionId,
                        addReversibleAction,
                        updateAnnotation
                    });
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
            }
        };
        _update();
    };
</script>

{#if annotation && selectionBox}
    {#key selectionBox}
        <SelectableSvgGroup
            groupId={annotation.sample_id}
            onSelect={toggleAnnotationSelection}
            box={selectionBox}
        >
            <SampleAnnotation
                {annotation}
                showLabel={$showAnnotationTextLabelsStore}
                imageWidth={sample.width}
                constraintBox={{
                    x: 0,
                    y: 0,
                    width: sample.width,
                    height: sample.height
                }}
                {isResizable}
                {onBoundingBoxChanged}
                {highlight}
                {scale}
            />
        </SelectableSvgGroup>
    {/key}
{/if}
