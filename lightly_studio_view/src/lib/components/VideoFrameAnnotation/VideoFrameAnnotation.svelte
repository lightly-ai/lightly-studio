<script lang="ts">
    import { SampleAnnotation, SelectableSvgGroup } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import type { BoundingBox } from '$lib/types';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
    import type { VideoFrameView } from '$lib/api/lightly_studio_local';
    import { getBoundingBox } from '../SampleAnnotation/utils';

    const {
        isSelected,
        annotationId,
        sample,
        datasetId,
        isResizable = false,
        toggleAnnotationSelection
    }: {
        sampleId: string;
        datasetId: string;
        isSelected: boolean;
        annotationId: string;
        isResizable?: boolean;
        sample: VideoFrameView;
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
                imageWidth={sample.video.width}
                constraintBox={{
                    x: 0,
                    y: 0,
                    width: sample.video.width,
                    height: sample.video.height
                }}
                {isResizable}
                {onBoundingBoxChanged}
            />
        </SelectableSvgGroup>
    {/key}
{/if}
