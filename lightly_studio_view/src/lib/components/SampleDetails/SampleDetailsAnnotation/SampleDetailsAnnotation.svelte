<script lang="ts">
    import { SampleAnnotation } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSample } from '$lib/hooks/useSample/useSample';
    import { getBoundingBox } from '../../SampleAnnotation/utils';
    import type { BoundingBox } from '$lib/types';
    import SelectableSvgGroup from '../../SelectableSvgGroup/SelectableSvgGroup.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';

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

    const { showAnnotationTextLabelsStore } = useSettings();

    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    const { sample } = $derived(
        useSample({
            sampleId,
            datasetId
        })
    );

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
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
            }
        };
        _update();
    };
</script>

{#if annotation && $sample.data && selectionBox}
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
                imageWidth={$sample.data.width}
                constraintBox={{
                    x: 0,
                    y: 0,
                    width: $sample.data.width,
                    height: $sample.data.height
                }}
                {isResizable}
                {onBoundingBoxChanged}
            />
        </SelectableSvgGroup>
    {/key}
{/if}
