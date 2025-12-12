<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';

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
    const { addReversibleAction } = useGlobalStorage();
    const { showAnnotationTextLabelsStore } = useSettings();

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    const { image } = $derived(useImage({ sampleId }));

    let selectionBox = $derived(annotation ? getBoundingBox(annotation!) : undefined);

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
                        dataset_id: datasetId,
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

{#if annotation && $image.data && selectionBox}
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
