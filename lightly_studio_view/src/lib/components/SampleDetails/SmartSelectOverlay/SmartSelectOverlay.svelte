<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        decodeRLEToBinaryMask,
        encodeBinaryMaskToRLE
    } from '$lib/components/SampleAnnotation/utils';
    import SampleAnnotationSegmentationRLE from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/SampleAnnotationSegmentationRLE.svelte';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { page } from '$app/state';

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number; annotations: AnnotationView[] };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        outputType?: 'mask' | 'box';
        annotationLabel?: string | null;
        annotationSource?: string | null;
    }

    let {
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        outputType = 'mask',
        annotationLabel,
        annotationSource
    }: Props = $props();
    let points = $state<{ x: number; y: number; positive: boolean }[]>([]);
    let previewMask = $state<Uint8Array | null>(null);
    let previewRle = $state<number[] | null>(null);
    let previewBox = $state<{ x: number; y: number; width: number; height: number } | null>(null);
    let predictedClass = $state<string | null>(null);
    let latencyMs = $state<number | null>(null);
    let sequence = 0;
    const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => collectionId });
    const { createLabel } = useCreateLabel({ getCollectionId: () => collectionId });
    const labels = useAnnotationLabels(() => ({ collectionId }));

    const pointFromEvent = (event: PointerEvent) => {
        if (!interactionRect) return null;
        const rect = interactionRect.getBoundingClientRect();
        return {
            x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
            y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
            positive: !event.shiftKey
        };
    };

    const classFromDetectionAtPoint = (point: { x: number; y: number; positive: boolean }) => {
        if (!point.positive) return null;
        const x = point.x * sample.width;
        const y = point.y * sample.height;
        return (
            sample.annotations
                .filter(
                    (annotation) =>
                        annotation.annotation_type === AnnotationType.OBJECT_DETECTION &&
                        annotation.object_detection_details &&
                        x >= annotation.object_detection_details.x &&
                        y >= annotation.object_detection_details.y &&
                        x <=
                            annotation.object_detection_details.x +
                                annotation.object_detection_details.width &&
                        y <=
                            annotation.object_detection_details.y +
                                annotation.object_detection_details.height
                )
                .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))[0]?.annotation_label
                .annotation_label_name ?? null
        );
    };

    const infer = async () => {
        if (!points.length || !points.some((point) => point.positive)) return;
        const requestSequence = ++sequence;
        const started = performance.now();
        const response = await fetch('/api/annotate/interactive', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ collection_id: collectionId, sample_id: sampleId, points })
        });
        if (!response.ok) {
            toast.error('Smart select inference failed');
            return;
        }
        const result = await response.json();
        if (requestSequence !== sequence) return;
        latencyMs = Math.round(performance.now() - started);
        previewBox = result.prediction?.bbox ?? null;
        previewRle = result.prediction?.segmentation_mask ?? null;
        predictedClass = predictedClass || result.prediction?.class_name?.trim() || null;
        previewMask =
            result.prediction?.segmentation_mask && previewBox
                ? decodeRLEToBinaryMask(
                      result.prediction.segmentation_mask,
                      previewBox.width,
                      previewBox.height
                  )
                : null;
    };

    const commit = async () => {
        if (!previewMask && !previewBox) return;
        const body =
            outputType === 'mask' && previewMask
                ? {
                      annotation_type: AnnotationType.SEGMENTATION_MASK,
                      segmentation_mask: encodeBinaryMaskToRLE(toFullImageMask(previewMask)),
                      x: previewBox?.x ?? 0,
                      y: previewBox?.y ?? 0,
                      width: previewBox?.width ?? 0,
                      height: previewBox?.height ?? 0,
                      annotation_label_name: predictedClass || annotationLabel
                  }
                : {
                      annotation_type: AnnotationType.OBJECT_DETECTION,
                      ...previewBox,
                      annotation_label_name: predictedClass || annotationLabel
                  };
        const name = predictedClass || annotationLabel || 'object';
        try {
            let label = labels.data?.find((item) => item.annotation_label_name === name);
            if (!label) {
                label = await createLabel({
                    dataset_id: page.params.dataset_id!,
                    annotation_label_name: name
                });
            }
            await createAnnotation({
                parent_sample_id: sampleId,
                annotation_label_id: label.annotation_label_id!,
                annotation_collection_name: annotationSource || undefined,
                ...body
            });
            previewMask = null;
            previewRle = null;
            previewBox = null;
            predictedClass = null;
            points = [];
            refetch();
        } catch {
            toast.error('Could not commit smart select annotation');
        }
    };

    const toFullImageMask = (croppedMask: Uint8Array): Uint8Array => {
        const fullMask = new Uint8Array(sample.width * sample.height);
        if (!previewBox) return fullMask;
        for (let y = 0; y < previewBox.height; y += 1) {
            for (let x = 0; x < previewBox.width; x += 1) {
                const targetX = previewBox.x + x;
                const targetY = previewBox.y + y;
                if (targetX < sample.width && targetY < sample.height) {
                    fullMask[targetY * sample.width + targetX] =
                        croppedMask[y * previewBox.width + x];
                }
            }
        }
        return fullMask;
    };

    const discard = () => {
        previewMask = null;
        previewRle = null;
        previewBox = null;
        predictedClass = null;
        points = [];
    };
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            if (previewMask || previewBox) void commit();
            else void infer();
        }
        if (event.key === 'Escape') {
            event.preventDefault();
            discard();
        }
    };
    onMount(() => window.addEventListener('keydown', onKeyDown));
    onDestroy(() => window.removeEventListener('keydown', onKeyDown));
</script>

{#if previewBox}
    {#if previewRle}
        <g transform={`translate(${previewBox.x} ${previewBox.y})`}>
            <SampleAnnotationSegmentationRLE
                width={previewBox.width}
                segmentation={previewRle}
                colorFill="rgba(34, 197, 94, 0.55)"
                opacity={0.85}
            />
        </g>
    {/if}
    <rect
        x={previewBox.x}
        y={previewBox.y}
        width={previewBox.width}
        height={previewBox.height}
        fill="none"
        stroke="#86efac"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-dasharray="6 5"
    />
{/if}
{#each points as point}
    <g
        transform={`translate(${point.x * sample.width} ${point.y * sample.height})`}
        pointer-events="none"
    >
        <circle
            r={Math.max(9, sample.width / 170)}
            fill="rgba(15, 23, 42, 0.9)"
            stroke="white"
            stroke-width="2"
        />
        <circle
            r={Math.max(6, sample.width / 240)}
            fill={point.positive ? '#10b981' : '#f43f5e'}
            stroke={point.positive ? '#a7f3d0' : '#fecdd3'}
            stroke-width="1.5"
        />
        <text
            text-anchor="middle"
            dominant-baseline="central"
            fill="white"
            font-size={Math.max(9, sample.width / 260)}
            font-weight="700">{point.positive ? '+' : '-'}</text
        >
    </g>
{/each}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={(event) => {
        const point = pointFromEvent(event);
        if (point) {
            points = [...points, point];
            previewMask = null;
            previewRle = null;
            previewBox = null;
            predictedClass = classFromDetectionAtPoint(point) || predictedClass;
        }
    }}
/>
{#if latencyMs !== null}
    <text
        x="8"
        y="24"
        fill="white"
        stroke="black"
        stroke-width="3"
        paint-order="stroke"
        font-size="14">{latencyMs} ms</text
    >
{/if}
