<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { getColorByLabel } from '$lib/utils';

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
        // LIG-9521 prototype: reports the generated crop blob URL so the grid can use
        // it as drag-to-search payload.
        onCropImageUrlChange?: (annotationId: string, url: string | null) => void;
    };

    let {
        annotation,
        containerWidth,
        containerHeight,
        sample,
        showLabel = true,
        selected = false,
        onCropImageUrlChange
    }: Props = $props();

    const padding = 20;

    const { isHidden } = useHideAnnotations();
    const { customLabelColorsStore } = useCustomLabelColors();

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

    // Render the visible window (padded bbox crop) into a canvas and use the result as
    // the <img> source, so the browser's native right-click "Copy image" copies exactly
    // the crop instead of the whole parent image (see PR #556 for images).
    let cropImageUrl = $state<string | null>(null);

    // Captured by value at init: props are lazy getters, and reading `annotation` during
    // effect cleanup would re-evaluate `annotations[index]` in the grid against an
    // already-shrunken array (crash on filter changes). The id is constant per instance —
    // the {#key} wrapper in the grid remounts this component when it changes.
    const annotationId = annotation.sample_id;

    $effect(() => {
        const sourceUrl = sample.url;
        const sampleWidth = sample.width;
        const sampleHeight = sample.height;
        const windowWidth = containerWidth / scale;
        const windowHeight = containerHeight / scale;
        const windowX = -xOffset / scale;
        const windowY = -yOffset / scale;
        if (!sourceUrl) return;

        let cancelled = false;
        let objectUrl: string | null = null;
        const imageElement = new Image();
        // The thumbnail may be served cross-origin (dev server); without this the
        // canvas would be tainted and toBlob would throw.
        imageElement.crossOrigin = 'anonymous';
        imageElement.onload = () => {
            if (cancelled) return;
            // The thumbnail can be downscaled relative to the original image size the
            // crop geometry is expressed in.
            const resolutionX = imageElement.naturalWidth / sampleWidth;
            const resolutionY = imageElement.naturalHeight / sampleHeight;
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.round(windowWidth * resolutionX));
            canvas.height = Math.max(1, Math.round(windowHeight * resolutionY));
            const context = canvas.getContext('2d');
            if (!context) return;
            context.fillStyle = '#000';
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.drawImage(
                imageElement,
                -windowX * resolutionX,
                -windowY * resolutionY,
                imageElement.naturalWidth,
                imageElement.naturalHeight
            );
            canvas.toBlob((blob) => {
                if (!blob || cancelled) return;
                objectUrl = URL.createObjectURL(blob);
                cropImageUrl = objectUrl;
                onCropImageUrlChange?.(annotationId, objectUrl);
            }, 'image/png');
        };
        imageElement.src = sourceUrl;

        return () => {
            cancelled = true;
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                onCropImageUrlChange?.(annotationId, null);
            }
        };
    });
</script>

{#if sample}
    <div
        class="crop rounded-lg bg-black"
        class:grid-item-selected={selected}
        style={`
        width: ${containerWidth}px;
        height: ${containerHeight}px;
    `}
    >
        <!-- Real <img> instead of a CSS background so the browser's native
             right-click "Copy image" works; the source is the canvas-rendered
             crop so only the crop gets copied (see PR #556 for images). -->
        {#if cropImageUrl}
            <img
                src={cropImageUrl}
                alt=""
                draggable="false"
                class="crop-image"
                style={`
                left: 0;
                top: 0;
                width: ${containerWidth}px;
                height: ${containerHeight}px;
            `}
            />
        {/if}
        <div
            class="annotation-box pointer-events-none"
            class:invisible={$isHidden}
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

    .crop-image {
        position: absolute;
        max-width: none;
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
