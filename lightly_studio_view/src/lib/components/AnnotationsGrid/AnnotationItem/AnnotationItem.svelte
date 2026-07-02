<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationClassVisibility } from '$lib/hooks';
    import { getColorByLabel } from '$lib/utils';
    import type { CropWindow } from './renderCropObjectUrl';

    type Props = {
        annotation: AnnotationView;
        containerWidth: number;
        containerHeight: number;
        showLabel: boolean;
        sample: {
            width: number;
            height: number;
            url: string;
        };
        selected?: boolean;
        // Reports the crop geometry so the grid can render the drag-to-search preview
        // lazily (on drag start) instead of eagerly per visible tile. `null` on unmount.
        onCropWindowChange?: (annotationId: string, window: CropWindow | null) => void;
    };

    let {
        annotation,
        containerWidth,
        containerHeight,
        sample,
        showLabel = true,
        selected = false,
        onCropWindowChange
    }: Props = $props();

    const padding = 20;

    const { isHidden } = useHideAnnotations();
    const { customLabelColorsStore } = useCustomLabelColors();
    const { isClassHidden } = useAnnotationClassVisibility();

    if (!annotation.object_detection_details && !annotation.segmentation_details) {
        throw new Error(
            'Unsupported annotation: Only annotations with object_detection_details or segmentation_details are supported. Please check the annotation data.'
        );
    }

    const {
        width: annotationWidth,
        height: annotationHeight,
        x: annotationX,
        y: annotationY
    } = getBoundingBox(annotation);

    const segmentationMask = annotation?.segmentation_details?.segmentation_mask;
    // Calculate values directly without using state
    const scale = $derived(
        Math.min(
            containerWidth / (annotationWidth + padding * 2),
            containerHeight / (annotationHeight + padding * 2)
        )
    );

    function getXOffset() {
        return (
            -(annotationX - padding) * scale +
            (containerWidth - (annotationWidth + padding * 2) * scale) / 2
        );
    }

    function getYOffset() {
        return (
            -(annotationY - padding) * scale +
            (containerHeight - (annotationHeight + padding * 2) * scale) / 2
        );
    }

    let labelName = annotation.annotation_label.annotation_label_name;
    const isAnnotationClassHidden = isClassHidden(labelName);

    const colorStroke = $derived.by(
        () => $customLabelColorsStore[labelName]?.color ?? getColorByLabel(labelName, 1).color
    );
    const colorFill = $derived.by(() => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const color = $customLabelColorsStore[labelName]?.color;
        return getColorByLabel(labelName, 0.4).color;
    });
    const opacity = $derived($customLabelColorsStore[labelName]?.alpha ?? 0.4);

    const isRLESegmentation = !!segmentationMask;

    // Calculate values for use in template
    const xOffset = $derived(getXOffset());
    const yOffset = $derived(getYOffset());

    // Captured by value at init: props are lazy getters, and reading `annotation` during
    // effect cleanup would re-evaluate `annotations[index]` in the grid against an
    // already-shrunken array (crash on filter changes). The id is constant per instance —
    // the {#key} wrapper in the grid remounts this component when it changes.
    const annotationId = annotation.sample_id;

    // Report the crop geometry (not a rendered image) upward. The grid turns it into a
    // preview blob only when a drag actually starts, so no canvas work happens per tile.
    $effect(() => {
        if (!sample.url) return;
        onCropWindowChange?.(annotationId, {
            sourceUrl: sample.url,
            sampleWidth: sample.width,
            sampleHeight: sample.height,
            windowWidth: containerWidth / scale,
            windowHeight: containerHeight / scale,
            windowX: -xOffset / scale,
            windowY: -yOffset / scale
        });
        return () => onCropWindowChange?.(annotationId, null);
    });
</script>

{#if sample}
    <div
        class="crop rounded-lg bg-black"
        class:grid-item-selected={selected}
        style={`
        width: ${containerWidth}px;
        height: ${containerHeight}px;
        background-image: url("${sample.url}");
        background-position: ${xOffset}px ${yOffset}px;
        background-size: ${sample.width * scale}px ${sample.height * scale}px;
        background-repeat: no-repeat;
    `}
    >
        <div
            class="annotation-box"
            class:invisible={$isHidden || $isAnnotationClassHidden}
            style={`
            left: ${(containerWidth - annotationWidth * scale) / 2}px;
            top: ${(containerHeight - annotationHeight * scale) / 2}px;
            width: ${annotationWidth * scale}px;
            height: ${annotationHeight * scale}px;
            border-color: ${isRLESegmentation ? 'transparent' : (colorStroke ?? getColorByLabel(labelName).color)};
            background-color: ${isRLESegmentation ? 'transparent' : (colorFill ?? getColorByLabel(labelName, 0.4).color)};
            border-style: solid;
            
        `}
        >
            {#if showLabel}
                <div
                    class="annotation-label flex items-center gap-1.5 text-sm text-white"
                    style={`background-color: ${colorFill ?? getColorByLabel(labelName, 0.4).color};`}
                >
                    <span class="truncate text-sm">{labelName}</span>
                    {#if annotation.object_track_number != null}
                        <span class="shrink-0 font-mono text-xs opacity-80"
                            >#{annotation.object_track_number}</span
                        >
                    {/if}
                </div>
            {/if}
            {#if isRLESegmentation}
                <svg
                    viewBox={`${annotationX} ${annotationY} ${annotationWidth} ${annotationHeight}`}
                >
                    <SampleAnnotationSegmentationRLE
                        segmentation={segmentationMask}
                        width={sample.width}
                        {colorFill}
                        {opacity}
                    />
                </svg>
            {/if}
        </div>
    </div>
{:else}
    <div
        class="crop flex items-center justify-center rounded-lg bg-black"
        style={`width: ${containerWidth}px; height: ${containerHeight}px;`}
    >
        <div class="text-xs text-gray-400">Loading...</div>
    </div>
{/if}

<style>
    .crop {
        position: relative;
        overflow: hidden;
    }

    .annotation-box {
        position: absolute;
        border: 1px solid rgba(0, 0, 0, 0);
        box-sizing: content-box;
    }

    .annotation-label {
        position: absolute;
        transform: translate3d(-1px, -100%, 0);
        padding: 1px 6px 2px;
        white-space: nowrap;
        cursor: pointer;
        user-select: none;
    }
</style>
