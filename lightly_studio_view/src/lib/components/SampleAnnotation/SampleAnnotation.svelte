<script lang="ts">
    import {
        SampleAnnotationBox,
        SampleAnnotationLabel,
        SampleAnnotationSegmentationRLE
    } from '$lib/components';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import type { Annotation } from '$lib/services/types';
    import type { BoundingBox } from '$lib/types';
    import { getColorByLabel } from '$lib/utils';
    import { getConstrainedCoordinates } from '$lib/utils/getConstrainedCoordinates';
    import ResizableRectangle from '../ResizableRectangle/ResizableRectangle.svelte';
    import { getBoundingBox, withAlpha } from './utils';

    const {
        annotation,
        imageWidth,
        showLabel = false,
        showBoundingBox = true,
        isResizable = false,
        scale = 1,
        constraintBox,
        onBoundingBoxChanged,
        highlight = 'auto',
        prerenderedDataUrl,
        prerenderedHeight
    }: {
        annotation: Annotation;
        showLabel?: boolean;
        showBoundingBox?: boolean;
        imageWidth: number;
        isResizable?: boolean;
        scale?: number;
        constraintBox?: BoundingBox;
        onBoundingBoxChanged?: (newBbox: BoundingBox) => void;
        highlight?: 'active' | 'disabled' | 'auto';
        prerenderedDataUrl?: string;
        prerenderedHeight?: number;
    } = $props();

    const { customLabelColorsStore } = useCustomLabelColors();
    const { selectedCollectionIds, collectionIdToName } = useAnnotationCollectionsFilter();

    const label = $derived(annotation.annotation_label.annotation_label_name);

    const colorLabel = $derived.by(() => {
        if ($selectedCollectionIds.length === 0) return label;
        return $collectionIdToName[annotation.annotation_collection_id] ?? label;
    });

    const segmentationMask = annotation?.segmentation_details?.segmentation_mask;

    const annotationId = $derived(annotation.sample_id);

    const colorText = $derived(getColorByLabel(colorLabel, 1));

    const colorStroke = $derived.by(() => {
        const color =
            $customLabelColorsStore[colorLabel]?.color ?? getColorByLabel(colorLabel, 1).color;
        if (highlight === 'disabled') return withAlpha(color, 0.1);
        return color;
    });

    const colorFill = $derived.by(() => {
        const color =
            $customLabelColorsStore[colorLabel]?.color ?? getColorByLabel(colorLabel, 0.4).color;

        if (highlight === 'disabled') return withAlpha(color, 0.1);
        if (highlight === 'active') return withAlpha(color, 0);
        return color;
    });

    const segmentationMaskOpacity = $derived.by(() => {
        if (highlight === 'disabled') {
            return 0.15;
        }

        return segmentationMask ? 0.65 : ($customLabelColorsStore[colorLabel]?.alpha ?? 1.0) * 0.6;
    });

    // Do not fill the bounding box if the annotation contains a segmentation mask.
    const boundingBoxOpacity = $derived(
        segmentationMask ? 0 : ($customLabelColorsStore[colorLabel]?.alpha ?? 1.0) * 0.4
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

    const showAnnotationLabel = $derived(
        showLabel &&
            (highlight === 'auto' || highlight === 'active') &&
            (annotation.annotation_type !== 'segmentation_mask' || showBoundingBox)
    );
</script>

<g data-annotation-label={label} data-testid="sample-annotation" data-annotation-id={annotationId}>
    {#if showAnnotationLabel}
        <SampleAnnotationLabel
            coordinates={[boundingBox.x, boundingBox.y]}
            {colorText}
            {label}
            trackId={annotation.object_track_number}
        />
    {/if}

    {#if segmentationMask}
        <SampleAnnotationSegmentationRLE
            segmentation={segmentationMask}
            width={imageWidth}
            {colorFill}
            opacity={segmentationMaskOpacity}
            {prerenderedDataUrl}
            {prerenderedHeight}
        />
    {/if}

    {#if showBoundingBox}
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
    {/if}
</g>
