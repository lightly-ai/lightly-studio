<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { getAnnotationsByParentSample, type OverlayAnnotationView } from '$lib/api/evaluationRunApi';
    import { AnnotationCanvas } from '$lib/components';
    import type { SampleImageObjectFit } from '../SampleImage/types';

    const {
        sampleId,
        sampleWidth,
        sampleHeight,
        collectionId,
        color,
        confidenceThreshold,
        objectFit = 'contain'
    }: {
        sampleId: string;
        sampleWidth: number;
        sampleHeight: number;
        collectionId: string;
        color: string;
        confidenceThreshold: number;
        objectFit?: SampleImageObjectFit;
    } = $props();

    const query = createQuery({
        queryKey: ['overlay_annotations', collectionId, sampleId],
        queryFn: () => getAnnotationsByParentSample(collectionId, sampleId)
    });

    const annotations = $derived(
        ($query.data ?? [])
            .filter(
                (a: OverlayAnnotationView) =>
                    a.object_detection_details !== null &&
                    (a.confidence === null || (a.confidence ?? 0) >= confidenceThreshold)
            )
            .map((a: OverlayAnnotationView) => ({
                annotation_type: 'object_detection' as const,
                annotation_label_name: a.annotation_label.annotation_label_name,
                object_detection_details: a.object_detection_details!
            }))
    );

    const objectFitClass = $derived(objectFit === 'cover' ? 'object-cover' : 'object-contain');
</script>

{#if annotations.length > 0}
    <AnnotationCanvas
        {sampleId}
        width={sampleWidth}
        height={sampleHeight}
        {annotations}
        alpha={0.8}
        overrideColor={color}
        className={`pointer-events-none absolute inset-0 z-[2] h-full w-full ${objectFitClass}`}
    />
{/if}
