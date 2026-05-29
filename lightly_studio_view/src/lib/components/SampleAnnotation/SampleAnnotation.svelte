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
    const { selectedCollectionIds, collectionIdToName, collectionIdToColor } =
        useAnnotationCollectionsFilter();

    const label = $derived(annotation.annotation_label.annotation_label_name);

    const colorLabel = $derived.by(() => {
        if ($selectedCollectionIds.length < 2) return label;
        return $collectionIdToName[annotation.annotation_collection_id] ?? label;
    });

    const segmentationMask = annotation?.segmentation_details?.segmentation_mask;

    const annotationId = $derived(annotation.sample_id);

    // Resolve hex color string from collection store or fall back to label-based color.
    const applyAlphaToColor = (color: string, alpha: number): string => {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return withAlpha(color, alpha);
    };

    // When in multi-collection mode, use the shared collection color; otherwise use label color.
    const baseColor = $derived.by(() => {
        if ($selectedCollectionIds.length > 1) {
            const hexColor = $collectionIdToColor[annotation.annotation_collection_id];
            if (hexColor) return hexColor;
        }
        return $customLabelColorsStore[colorLabel]?.color ?? getColorByLabel(colorLabel, 1).color;
    });

    const colorText = $derived.by(() => {
        const color = applyAlphaToColor(baseColor, 1);
        // Derive a contrast color by inverting the RGB components
        const rgba = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        const contrastColor = rgba
            ? `rgba(${255 - parseInt(rgba[1])}, ${255 - parseInt(rgba[2])}, ${255 - parseInt(rgba[3])}, 1)`
            : color;
        return { color, contrastColor };
    });

    const colorStroke = $derived.by(() => {
        const color = applyAlphaToColor(baseColor, 1);
        if (highlight === 'disabled') return withAlpha(color, 0.1);
        return color;
    });

    const colorFill = $derived.by(() => {
        const color = applyAlphaToColor(baseColor, 0.4);
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
