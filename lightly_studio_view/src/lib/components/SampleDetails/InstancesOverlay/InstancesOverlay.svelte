<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
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
    import { onMount } from 'svelte';

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number; annotations: AnnotationView[] };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        prompt: string;
        onPromptChange: (prompt: string) => void;
        annotationClass?: string | null;
        isDrawingBox: boolean;
        onBoxDrawn: () => void;
        annotationLabel?: string | null;
        annotationSource?: string | null;
        outputType?: 'mask' | 'box';
        onStateChange: (state: {
            boxCount: number;
            canGenerate: boolean;
            isGenerating: boolean;
            resultCount: number;
            generate: () => void;
            save: () => void;
            clear: () => void;
        }) => void;
    }
    type Box = { x: number; y: number; width: number; height: number };
    type Prediction = {
        bbox: { x: number; y: number; width: number; height: number };
        segmentation_mask: number[];
        class_name?: string;
    };

    let {
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        prompt,
        onPromptChange,
        annotationClass,
        isDrawingBox,
        onBoxDrawn,
        annotationLabel,
        annotationSource,
        outputType = 'mask',
        onStateChange
    }: Props = $props();
    let boxes = $state<Box[]>([]);
    let dragStart = $state<{ x: number; y: number } | null>(null);
    let dragBox = $state<Box | null>(null);
    let predictions = $state<Prediction[]>([]);
    let isGenerating = $state(false);
    let previousPrompt = $state<string | undefined>(undefined);
    const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => collectionId });
    const { createLabel } = useCreateLabel({ getCollectionId: () => collectionId });
    const labels = useAnnotationLabels(() => ({ collectionId }));

    const point = (event: PointerEvent) => {
        if (!interactionRect) return null;
        const rect = interactionRect.getBoundingClientRect();
        return {
            x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
            y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
        };
    };
    const makeBox = (start: { x: number; y: number }, end: { x: number; y: number }): Box => ({
        x: Math.min(start.x, end.x),
        y: Math.min(start.y, end.y),
        width: Math.abs(end.x - start.x),
        height: Math.abs(end.y - start.y)
    });
    const notifyState = () =>
        onStateChange({
            boxCount: boxes.length,
            canGenerate: Boolean(prompt.trim() || boxes.length),
            isGenerating,
            resultCount: predictions.length,
            generate: () => void generate(),
            save: () => void save(),
            clear
        });
    const clear = () => {
        boxes = [];
        predictions = [];
        onPromptChange('');
        notifyState();
    };
    const deletePrediction = (index: number) => {
        predictions = predictions.filter((_, predictionIndex) => predictionIndex !== index);
        notifyState();
    };
    const generate = async () => {
        if (!prompt.trim() && boxes.length === 0) return;
        isGenerating = true;
        notifyState();
        try {
            const response = await fetch('/api/annotate/instances', {
                method: 'POST',
                headers: { 'content-type': 'application/json' },
                body: JSON.stringify({
                    collection_id: collectionId,
                    sample_id: sampleId,
                    prompt: prompt.trim() || null,
                    boxes: boxes.length ? boxes : null
                })
            });
            if (!response.ok) throw new Error();
            const result = await response.json();
            predictions = result.predictions ?? [];
            boxes = [];
            notifyState();
        } catch {
            toast.error('Instance generation failed');
        } finally {
            isGenerating = false;
            notifyState();
        }
    };
    const toFullMask = (prediction: Prediction) => {
        const mask = decodeRLEToBinaryMask(
            prediction.segmentation_mask,
            prediction.bbox.width,
            prediction.bbox.height
        );
        const full = new Uint8Array(sample.width * sample.height);
        for (let y = 0; y < prediction.bbox.height; y += 1)
            for (let x = 0; x < prediction.bbox.width; x += 1) {
                const tx = prediction.bbox.x + x;
                const ty = prediction.bbox.y + y;
                if (tx >= 0 && ty >= 0 && tx < sample.width && ty < sample.height)
                    full[ty * sample.width + tx] = mask[y * prediction.bbox.width + x];
            }
        return full;
    };
    const save = async () => {
        try {
            const labelsByName = new Map(
                (labels.data ?? []).map((label) => [label.annotation_label_name, label])
            );
            for (const prediction of predictions) {
                const name =
                    annotationClass?.trim() ||
                    prediction.class_name?.trim() ||
                    prompt.trim() ||
                    annotationLabel ||
                    'object';
                let label = labelsByName.get(name);
                if (!label) {
                    label = await createLabel({
                        dataset_id: page.params.dataset_id!,
                        annotation_label_name: name
                    });
                    labelsByName.set(name, label);
                }
                await createAnnotation({
                    parent_sample_id: sampleId,
                    annotation_label_id: label.annotation_label_id!,
                    annotation_collection_name: annotationSource || undefined,
                    ...(outputType === 'mask'
                        ? {
                              annotation_type: AnnotationType.SEGMENTATION_MASK,
                              segmentation_mask: encodeBinaryMaskToRLE(toFullMask(prediction))
                          }
                        : { annotation_type: AnnotationType.OBJECT_DETECTION }),
                    x: prediction.bbox.x,
                    y: prediction.bbox.y,
                    width: prediction.bbox.width,
                    height: prediction.bbox.height
                });
            }
            predictions = [];
            refetch();
            notifyState();
        } catch {
            toast.error('Could not save instances');
        }
    };
    $effect(() => {
        if (previousPrompt === undefined) {
            previousPrompt = prompt;
            return;
        }
        if (prompt === previousPrompt) return;

        previousPrompt = prompt;
        boxes = [];
        predictions = [];
        notifyState();
    });
    onMount(notifyState);
</script>

{#each predictions as prediction, index (index)}
    {#if outputType === 'mask'}
        <g transform={`translate(${prediction.bbox.x} ${prediction.bbox.y})`}>
            <SampleAnnotationSegmentationRLE
                width={prediction.bbox.width}
                segmentation={prediction.segmentation_mask}
                colorFill="rgba(34, 197, 94, 0.55)"
                opacity={0.85}
            />
        </g>
    {/if}
    <rect
        x={prediction.bbox.x}
        y={prediction.bbox.y}
        width={prediction.bbox.width}
        height={prediction.bbox.height}
        fill="none"
        stroke="#86efac"
        stroke-width="2"
        pointer-events="none"
    />
{/each}
{#if dragBox}<rect
        x={dragBox.x * sample.width}
        y={dragBox.y * sample.height}
        width={dragBox.width * sample.width}
        height={dragBox.height * sample.height}
        fill="rgba(59, 130, 246, 0.15)"
        stroke="#93c5fd"
        stroke-width="2"
        stroke-dasharray="6 5"
        pointer-events="none"
    />{/if}
{#each boxes as box}<rect
        x={box.x * sample.width}
        y={box.y * sample.height}
        width={box.width * sample.width}
        height={box.height * sample.height}
        fill="rgba(59, 130, 246, 0.12)"
        stroke="#60a5fa"
        stroke-width="2"
        pointer-events="none"
    />{/each}
{#if isDrawingBox}
    <SampleAnnotationRect
        bind:interactionRect
        {sample}
        cursor="crosshair"
        onpointerdown={(event) => {
            const next = point(event);
            if (!next) return;
            predictions = [];
            notifyState();
            event.currentTarget.setPointerCapture(event.pointerId);
            dragStart = next;
        }}
        onpointermove={(event) => {
            if (!dragStart) return;
            const next = point(event);
            if (next) dragBox = makeBox(dragStart, next);
        }}
        onpointerup={(event) => {
            if (!dragStart) return;
            const next = point(event);
            event.currentTarget.releasePointerCapture(event.pointerId);
            if (next) {
                const box = makeBox(dragStart, next);
                if (box.width > 0.005 && box.height > 0.005) {
                    boxes = [...boxes, box];
                    notifyState();
                }
            }
            dragStart = null;
            dragBox = null;
            onBoxDrawn();
        }}
        onpointercancel={(event) => {
            event.currentTarget.releasePointerCapture(event.pointerId);
            dragStart = null;
            dragBox = null;
            onBoxDrawn();
        }}
    />
{/if}
{#each predictions as prediction, index (index)}
    <foreignObject
        x={Math.max(0, prediction.bbox.x + prediction.bbox.width - 24)}
        y={Math.max(0, prediction.bbox.y - 24)}
        width="24"
        height="24"
        pointer-events="all"
    >
        <button
            type="button"
            class="flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90"
            aria-label={`Delete instance ${index + 1}`}
            title="Delete instance"
            onclick={(event) => {
                event.stopPropagation();
                deletePrediction(index);
            }}
            onpointerdown={(event) => event.stopPropagation()}
            onmousedown={(event) => event.stopPropagation()}
        >
            <Trash2 class="size-3.5" />
        </button>
    </foreignObject>
{/each}
