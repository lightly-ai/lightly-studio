<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import type { Annotation } from '$lib/services/types';
    import { getColorByLabel } from '$lib/utils';
    import { onMount } from 'svelte';

    type Props = {
        annotation: Annotation;
        width: number;
        height: number;
        cachedDatasetVersion: string;
        showLabel: boolean;
        selected?: boolean;
    };

    let {
        annotation,
        width,
        height,
        cachedDatasetVersion = '',
        showLabel = true,
        selected = false
    }: Props = $props();

    const padding = 20;
    const { sample: sampleQuery } = useImage({ sampleId: annotation.parent_sample_id });
    const { getDatasetVersion } = useGlobalStorage();
    const { isHidden } = useHideAnnotations();
    const { customLabelColorsStore } = useCustomLabelColors();

    // Store dataset version for cache busting
    let datasetVersion = $state(cachedDatasetVersion);
    let datasetVersionLoaded = $state(!!cachedDatasetVersion);

    // Get sample data from query
    const sample = $derived($sampleQuery.data);
    const isSampleLoaded = $derived($sampleQuery.isSuccess && !!sample);

    // Component is loaded when both dataset version and sample are loaded
    const isLoaded = $derived(datasetVersionLoaded && isSampleLoaded);

    onMount(async () => {
        // Only fetch dataset version if not already provided
        if (!cachedDatasetVersion && sample?.sample?.dataset_id) {
            datasetVersion = await getDatasetVersion(sample?.sample?.dataset_id);
            datasetVersionLoaded = true;
        }
    });

    if (!annotation.object_detection_details && !annotation.instance_segmentation_details) {
        throw new Error(
            'Unsupported annotation: Only annotations with object_detection_details or instance_segmentation_details are supported. Please check the annotation data.'
        );
    }

    const {
        width: annotationWidth,
        height: annotationHeight,
        x: annotationX,
        y: annotationY
    } = getBoundingBox(annotation);

    const segmentationMask = annotation?.instance_segmentation_details?.segmentation_mask;
    // Calculate values directly without using state
    const scale = $derived(
        Math.min(width / (annotationWidth + padding * 2), height / (annotationHeight + padding * 2))
    );

    function getXOffset() {
        return (
            -(annotationX - padding) * scale + (width - (annotationWidth + padding * 2) * scale) / 2
        );
    }

    function getYOffset() {
        return (
            -(annotationY - padding) * scale +
            (height - (annotationHeight + padding * 2) * scale) / 2
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

    // Force CSS background to reload by using an incrementally different URL
    // This is a more aggressive approach to force the browser to reload the image
    const uniqueImageUrl = $derived(
        sample
            ? `${PUBLIC_SAMPLES_URL}/sample/${annotation.parent_sample_id}${datasetVersion ? `?v=${datasetVersion}` : ''}`
            : ''
    );
</script>

{#if isLoaded && sample}
    <div
        class="crop rounded-lg bg-black"
        class:annotation-selected={selected}
        style={` 
        width: ${width}px;
        height: ${height}px;
        background-image: url("${uniqueImageUrl}");
        background-position: ${xOffset}px ${yOffset}px;
        background-size: ${sample.width * scale}px ${sample.height * scale}px;
        background-repeat: no-repeat;
    `}
    >
        <div
            class="annotation-box"
            class:invisible={$isHidden}
            style={`
            left: ${(width - annotationWidth * scale) / 2}px;
            top: ${(height - annotationHeight * scale) / 2}px;
            width: ${annotationWidth * scale}px;
            height: ${annotationHeight * scale}px;
            border-color: ${isRLESegmentation ? 'transparent' : (colorStroke ?? getColorByLabel(labelName).color)};
            background-color: ${isRLESegmentation ? 'transparent' : (colorFill ?? getColorByLabel(labelName, 0.4).color)};
            border-style: solid;
            
        `}
        >
            {#if showLabel}
                <div
                    class="annotation-label flex items-center justify-between text-sm text-white"
                    style={`background-color: ${colorFill ?? getColorByLabel(labelName, 0.4).color};`}
                >
                    <span class="truncate text-sm">{labelName}</span>
                </div>
            {/if}
            {#if isRLESegmentation && sample}
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
        style={`width: ${width}px; height: ${height}px;`}
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
    }

    .annotation-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
