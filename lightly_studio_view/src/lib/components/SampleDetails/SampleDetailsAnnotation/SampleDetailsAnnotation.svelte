<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        addAnnotationUpdateToUndoStack,
        BBOX_CHANGE_ANNOTATION_DETAILS
    } from '$lib/services/addAnnotationUpdateToUndoStack';
    import { beforeNavigate } from '$app/navigation';

    const {
        isSelected,
        annotationId,
        sampleId,
        datasetId,
        isResizable = false,
        toggleAnnotationSelection
    }: {
        sampleId: string;
        datasetId: string;
        isSelected: boolean;
        annotationId: string;
        isResizable?: boolean;
        toggleAnnotationSelection: (annotationId: string) => void;
    } = $props();
    const { addReversibleAction, clearReversibleActionsByGroupId } = useGlobalStorage();
    const { showAnnotationTextLabelsStore } = useSettings();

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    const { image } = $derived(useImage({ sampleId }));

    let selectionBox = $derived(
        $annotationResp.data ? getBoundingBox($annotationResp.data!) : undefined
    );

    const onBoundingBoxChanged = (bbox: BoundingBox) => {
        const _update = async () => {
            try {
                await updateAnnotation({
                    annotation_id: annotationId,
                    dataset_id: datasetId,
                    bounding_box: bbox
                });
                if (annotation)
                    addAnnotationUpdateToUndoStack({
                        annotation,
                        addReversibleAction,
                        updateAnnotation
                    });
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
            }
        };
        _update();
    };

    beforeNavigate(() => {
        clearReversibleActionsByGroupId(BBOX_CHANGE_ANNOTATION_DETAILS);
    });
</script>

{#if annotation && $image.data && selectionBox}
    {#key selectionBox}
        <SelectableSvgGroup
            groupId={annotation.annotation_id}
            onSelect={toggleAnnotationSelection}
            box={selectionBox}
            {isSelected}
        >
            <SampleAnnotation
                {annotation}
                showLabel={$showAnnotationTextLabelsStore}
                imageWidth={$image.data.width}
                constraintBox={{
                    x: 0,
                    y: 0,
                    width: $image.data.width,
                    height: $image.data.height
                }}
                {isResizable}
                {onBoundingBoxChanged}
            />
        </SelectableSvgGroup>
    {/key}
{/if}
