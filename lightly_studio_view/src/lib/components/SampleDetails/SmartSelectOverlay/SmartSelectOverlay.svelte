<script lang="ts">
    import { onDestroy, onMount, untrack } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { createMutation } from '@tanstack/svelte-query';
    import type {
        AnnotationPreview as Preview,
        AnnotationView
    } from '$lib/api/lightly_studio_local';
    import { createInteractiveAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { useSaveAnnotationPreviews } from '$lib/hooks/useSaveAnnotationPreviews';
    import { isTextInputTarget } from '$lib/utils';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '../AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '../AnnotationPreview/NormalizedBoxRect.svelte';
    import {
        boxFromPoints,
        getAnnotationPreviewErrorMessage,
        isDragBox,
        normalizedPointFromEvent,
        resolveAnnotationClassName,
        type NormalizedBox,
        type NormalizedPoint,
        type OutputType
    } from '../AnnotationPreview/annotationPreview.helpers';
    import SmartSelectPoints from './SmartSelectPoints.svelte';
    import {
        canInferFromPoints,
        getClassNameAtPoint,
        getPointSign,
        type SmartSelectPoint
    } from './SmartSelectOverlay.helpers';

    type SmartSelectPrompt = { points: SmartSelectPoint[] } | { boxes: NormalizedBox[] };

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number; annotations: AnnotationView[] };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        outputType: OutputType;
        annotationClass?: string | null;
        annotationSource?: string | null;
        positivePoints: boolean;
        negativePoints: boolean;
        boxes: boolean;
        onActionsChange: (actions: {
            canSave: boolean;
            save: () => void;
            clear: () => void;
        }) => void;
    }

    let {
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        outputType,
        annotationClass,
        annotationSource,
        positivePoints,
        negativePoints,
        boxes,
        onActionsChange
    }: Props = $props();

    let points = $state<SmartSelectPoint[]>([]);
    let dragStart = $state<NormalizedPoint | null>(null);
    let dragBox = $state<NormalizedBox | null>(null);
    let preview = $state<Preview | null>(null);
    let hintedClass = $state<string | null>(null);
    let latencyMs = $state<number | null>(null);
    let previewOutputType = $state<OutputType>('mask');
    let lastPrompt: SmartSelectPrompt | null = null;
    // Discards responses that a newer request or a clear made stale.
    let sequence = 0;

    const mutation = createMutation(() => createInteractiveAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => collectionId
    });

    const infer = async (prompt: SmartSelectPrompt) => {
        const requestSequence = ++sequence;
        const requestOutputType = outputType;
        lastPrompt = prompt;
        try {
            const result = await mutation.mutateAsync({
                body: {
                    collection_id: collectionId,
                    sample_id: sampleId,
                    output_type: requestOutputType,
                    ...prompt
                }
            });
            if (requestSequence !== sequence) return;
            latencyMs = Math.round(result.latency_ms);
            preview = result.prediction;
            previewOutputType = requestOutputType;
        } catch (error) {
            if (requestSequence !== sequence) return;
            toast.error(`Smart select failed: ${getAnnotationPreviewErrorMessage(error)}`);
        }
    };

    const clear = () => {
        sequence += 1;
        lastPrompt = null;
        preview = null;
        hintedClass = null;
        points = [];
        dragStart = null;
        dragBox = null;
    };

    const save = async () => {
        if (!preview) return;
        const className = resolveAnnotationClassName([
            annotationClass,
            hintedClass,
            preview.class_name
        ]);
        try {
            await saveAnnotationPreviews({
                sampleId,
                image: sample,
                outputType,
                annotationSource,
                previews: [{ preview, className }]
            });
            clear();
            refetch();
        } catch (error) {
            toast.error(
                `Could not save the annotation: ${getAnnotationPreviewErrorMessage(error)}`
            );
        }
    };

    $effect(() => {
        onActionsChange({ canSave: preview !== null, save: () => void save(), clear });
    });

    // A box preview has a rectangle mask, so the mask output needs a new request.
    $effect(() => {
        if (outputType !== 'mask') return;
        untrack(() => {
            if (previewOutputType === 'box' && lastPrompt) void infer(lastPrompt);
        });
    });

    const addPoint = (point: NormalizedPoint, shiftKey: boolean) => {
        const positive = getPointSign({ shiftKey, positivePoints, negativePoints });
        if (positive === null) return;
        const next = { ...point, positive };
        points = [...points, next];
        hintedClass = getClassNameAtPoint(sample.annotations, next, sample) ?? hintedClass;
        if (canInferFromPoints(points)) void infer({ points });
    };

    const pointFromEvent = (event: PointerEvent) =>
        interactionRect
            ? normalizedPointFromEvent(event, interactionRect.getBoundingClientRect())
            : null;

    const onPointerDown = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const point = pointFromEvent(event);
        if (!point) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        dragStart = point;
    };

    const onPointerMove = (event: PointerEvent) => {
        const point = pointFromEvent(event);
        if (!dragStart || !point || !boxes) return;
        const box = boxFromPoints(dragStart, point);
        dragBox = isDragBox(box) ? box : null;
    };

    const onPointerUp = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const start = dragStart;
        const box = dragBox;
        event.currentTarget.releasePointerCapture(event.pointerId);
        dragStart = null;
        dragBox = null;
        if (!start) return;
        if (box) {
            points = [];
            hintedClass = null;
            preview = null;
            void infer({ boxes: [box] });
            return;
        }
        addPoint(start, event.shiftKey);
    };

    const onPointerCancel = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        dragStart = null;
        dragBox = null;
    };

    const onKeyDown = (event: KeyboardEvent) => {
        if (isTextInputTarget(event.target)) return;
        if (event.key === 'Enter' && preview) {
            event.preventDefault();
            void save();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            clear();
        }
    };
    onMount(() => window.addEventListener('keydown', onKeyDown));
    onDestroy(() => window.removeEventListener('keydown', onKeyDown));
</script>

{#if preview}
    <AnnotationPreview {preview} {outputType} />
{/if}
{#if dragBox}
    <NormalizedBoxRect box={dragBox} image={sample} dashed />
{/if}
<SmartSelectPoints {points} image={sample} />
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={onPointerDown}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={onPointerCancel}
/>
{#if latencyMs !== null}
    <text
        x="8"
        y="24"
        fill="white"
        stroke="black"
        stroke-width="3"
        paint-order="stroke"
        font-size="14"
        pointer-events="none">{latencyMs} ms</text
    >
{/if}
