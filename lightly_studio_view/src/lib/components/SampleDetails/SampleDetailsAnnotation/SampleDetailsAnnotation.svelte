<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';

    const {
        isSelected,
        annotationId,
        collectionId,
        isResizable = false,
        sample,
        toggleAnnotationSelection
    }: {
        sampleId: string;
        collectionId: string;
        isSelected: boolean;
        annotationId: string;
        isResizable?: boolean;
        sample: {
            width: number;
            height: number;
        };
        toggleAnnotationSelection: (annotationId: string) => void;
    } = $props();
    const { addReversibleAction } = useGlobalStorage();
    const { showAnnotationTextLabelsStore } = useSettings();

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            collectionId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    let selectionBox = $derived(annotation ? getBoundingBox(annotation!) : undefined);

    const onBoundingBoxChanged = (bbox: BoundingBox) => {
        const _update = async () => {
            try {
                await updateAnnotation({
                    annotation_id: annotationId,
                    collection_id: collectionId,
                    bounding_box: bbox
                });
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
            {isSelected}
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
            />
        </SelectableSvgGroup>
    {/key}
{/if}
