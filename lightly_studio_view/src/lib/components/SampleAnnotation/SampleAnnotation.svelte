<script lang="ts">
    import {
        SampleAnnotationBox,
        SampleAnnotationLabel,
        SampleAnnotationSegmentationRLE
    } from '$lib/components';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import type { Annotation } from '$lib/services/types';
    import type { BoundingBox } from '$lib/types';
    import { getColorByLabel } from '$lib/utils';
    import { getConstrainedCoordinates } from '$lib/utils/getConstrainedCoordinates';
    import ResizableRectangle from '../ResizableRectangle/ResizableRectangle.svelte';
    import { getBoundingBox } from './utils';

    const {
        annotation,
        imageWidth,
        showLabel = false,
        isResizable = false,
        scale = 1,
        constraintBox,
        onBoundingBoxChanged
    }: {
        annotation: Annotation;
        showLabel?: boolean;
        imageWidth: number;
        isResizable?: boolean;
        scale?: number;
        constraintBox?: BoundingBox;
        onBoundingBoxChanged?: (newBbox: BoundingBox) => void;
    } = $props();

    const { customLabelColorsStore } = useCustomLabelColors();

    const label = $derived(annotation.annotation_label.annotation_label_name);

    const segmentationMask = annotation?.instance_segmentation_details?.segmentation_mask;

    const annotationId = $derived(annotation.sample_id);

    const colorText = $derived(getColorByLabel(label, 1));

    const colorStroke = $derived(
        $customLabelColorsStore[label]?.color ?? getColorByLabel(label, 1).color
    );

    const colorFill = $derived(
        $customLabelColorsStore[label]?.color ?? getColorByLabel(label, 0.4).color
    );

    const segmentationMaskOpacity = $derived(segmentationMask ? 0.65 : $customLabelColorsStore[label]?.alpha * 0.4);
    
    // Do not fill the bounding box if the annotation contains a segmentation mask.
    const boundingBoxOpacity = $derived(
        segmentationMask ? 0 : $customLabelColorsStore[label]?.alpha * 0.4
    );

    let boundingBox = $state<BoundingBox>(getBoundingBox(annotation));

    const onResize = (newBbox: BoundingBox) => {
        boundingBox = constraintBox
            ? getConstrainedCoordinates(newBbox, constraintBox, false)
            : newBbox;
    };

    const onMove = (newBbox: BoundingBox) => {
        boundingBox = constraintBox
            ? getConstrainedCoordinates(newBbox, constraintBox, true)
            : newBbox;
    };

    const onDragEnd = (newBbox: BoundingBox) => {
        const finalBbox = constraintBox
            ? getConstrainedCoordinates(newBbox, constraintBox, true)
            : newBbox;
        boundingBox = finalBbox;
        onBoundingBoxChanged?.(finalBbox);
    };
    const bbox: [number, number, number, number] = $derived([
        boundingBox.x,
        boundingBox.y,
        boundingBox.width,
        boundingBox.height
    ]);
</script>

<g data-annotation-label={label} data-testid="sample-annotation" data-annotation-id={annotationId}>
    {#if showLabel}
        <SampleAnnotationLabel coordinates={[boundingBox.x, boundingBox.y]} {colorText} {label} />
    {/if}

    {#if segmentationMask}
        <SampleAnnotationSegmentationRLE
            segmentation={segmentationMask}
            width={imageWidth}
            {colorFill}
            opacity={segmentationMaskOpacity}
        />
    {/if}

    <!--Disable resizable rectangle for segmentation masks since we don’t support it yet.-->
    {#if isResizable && constraintBox && !segmentationMask}
        <ResizableRectangle
            bind:bbox={boundingBox}
            {colorStroke}
            {colorFill}
            opacity={boundingBoxOpacity}
            {scale}
            {onResize}
            {onMove}
            {onDragEnd}
        />
    {:else}
        <SampleAnnotationBox
            {bbox}
            {annotationId}
            {label}
            {colorStroke}
            {colorFill}
            opacity={boundingBoxOpacity}
        />
    {/if}
</g>
