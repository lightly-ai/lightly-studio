<script lang="ts">
    import { untrack } from 'svelte';
    import { toast } from 'svelte-sonner';
    import { createMutation } from '@tanstack/svelte-query';
    import type { AnnotationPreview as Preview } from '$lib/api/lightly_studio_local';
    import { createInstancesAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { useSaveAnnotationPreviews } from '$lib/hooks/useSaveAnnotationPreviews';
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
    import { buildInstancesRequestBody, canGenerateInstances } from './InstancesOverlay.helpers';
    import InstanceDeleteButton from './InstanceDeleteButton.svelte';

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        prompt: string;
        onPromptChange: (prompt: string) => void;
        maxInstances: number;
        annotationClass?: string | null;
        annotationSource?: string | null;
        outputType: OutputType;
        isDrawingBox: boolean;
        onBoxDrawn: () => void;
        onStateChange: (state: {
            boxCount: number;
            isGenerating: boolean;
            resultCount: number;
            generate: () => void;
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
        prompt,
        onPromptChange,
        maxInstances,
        annotationClass,
        annotationSource,
        outputType,
        isDrawingBox,
        onBoxDrawn,
        onStateChange
    }: Props = $props();

    let boxes = $state<NormalizedBox[]>([]);
    let dragStart = $state<NormalizedPoint | null>(null);
    let dragBox = $state<NormalizedBox | null>(null);
    let predictions = $state<Preview[]>([]);
    let isGenerating = $state(false);
    let predictionsOutputType = $state<OutputType>('mask');
    let previousPrompt = untrack(() => prompt);

    const mutation = createMutation(() => createInstancesAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => collectionId
    });

    const generate = async () => {
        if (!canGenerateInstances({ prompt, boxCount: boxes.length })) return;
        isGenerating = true;
        try {
            const result = await mutation.mutateAsync({
                body: buildInstancesRequestBody({
                    collectionId,
                    sampleId,
                    prompt,
                    boxes,
                    maxInstances,
                    outputType
                })
            });
            predictions = result.predictions;
            predictionsOutputType = outputType;
            boxes = [];
        } catch (error) {
            toast.error(`Finding instances failed: ${getAnnotationPreviewErrorMessage(error)}`);
        } finally {
            isGenerating = false;
        }
    };

    const save = async () => {
        try {
            await saveAnnotationPreviews({
                sampleId,
                image: sample,
                outputType,
                annotationSource,
                previews: predictions.map((preview) => ({
                    preview,
                    className: resolveAnnotationClassName([
                        annotationClass,
                        preview.class_name,
                        prompt
                    ])
                }))
            });
            predictions = [];
            refetch();
        } catch (error) {
            toast.error(`Could not save the instances: ${getAnnotationPreviewErrorMessage(error)}`);
        }
    };

    const clear = () => {
        boxes = [];
        predictions = [];
        onPromptChange('');
    };

    $effect(() => {
        onStateChange({
            boxCount: boxes.length,
            isGenerating,
            resultCount: predictions.length,
            generate: () => void generate(),
            save: () => void save(),
            clear
        });
    });

    // A new prompt starts a new search.
    $effect(() => {
        if (prompt === previousPrompt) return;
        previousPrompt = prompt;
        boxes = [];
        predictions = [];
    });

    // Box results have rectangle masks, so the mask output needs a new search.
    $effect(() => {
        if (outputType === 'mask' && untrack(() => predictionsOutputType) === 'box') {
            predictions = [];
            predictionsOutputType = 'mask';
        }
    });

    const pointFromEvent = (event: PointerEvent) =>
        interactionRect
            ? normalizedPointFromEvent(event, interactionRect.getBoundingClientRect())
            : null;

    const finishDrag = (
        event: PointerEvent & { currentTarget: SVGRectElement },
        keepBox: boolean
    ) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        if (keepBox && dragBox && isDragBox(dragBox)) boxes = [...boxes, dragBox];
        dragStart = null;
        dragBox = null;
        onBoxDrawn();
    };
</script>

{#each predictions as preview, index (index)}
    <AnnotationPreview {preview} {outputType} />
{/each}
{#if dragBox}
    <NormalizedBoxRect box={dragBox} image={sample} dashed />
{/if}
{#each boxes as box, index (index)}
    <NormalizedBoxRect {box} image={sample} />
{/each}
{#if isDrawingBox}
    <SampleAnnotationRect
        bind:interactionRect
        {sample}
        cursor="crosshair"
        onpointerdown={(event) => {
            const point = pointFromEvent(event);
            if (!point) return;
            predictions = [];
            event.currentTarget.setPointerCapture(event.pointerId);
            dragStart = point;
        }}
        onpointermove={(event) => {
            const point = pointFromEvent(event);
            if (dragStart && point) dragBox = boxFromPoints(dragStart, point);
        }}
        onpointerup={(event) => finishDrag(event, true)}
        onpointercancel={(event) => finishDrag(event, false)}
    />
{/if}
{#each predictions as preview, index (index)}
    <InstanceDeleteButton
        bbox={preview.bbox}
        {index}
        onDelete={() => (predictions = predictions.filter((_, i) => i !== index))}
    />
{/each}
