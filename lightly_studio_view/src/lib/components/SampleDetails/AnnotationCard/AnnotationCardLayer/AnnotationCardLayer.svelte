<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useGlobalStorage, usePendingBoxClass } from '$lib/hooks';
    import AnnotationCard from '../AnnotationCard.svelte';
    import { PendingBoxCard } from '../PendingBoxCard';

    // The cards over the canvas: the class picker of a drawn box, else the card of the selected
    // box or mask, for class, source and delete. The cards hide themselves while drawing.
    interface Props {
        /** The collection that owns the annotation classes and sources. */
        collectionId: string;
        /** The annotations on the canvas. */
        annotations: AnnotationView[];
        selectedAnnotationId: string | null | undefined;
        refetch: () => void;
        getLayer: () => SVGGraphicsElement | null;
        colorBySource: boolean;
    }

    const {
        collectionId,
        annotations,
        selectedAnnotationId,
        refetch,
        getLayer,
        colorBySource
    }: Props = $props();
    const { isEditingMode } = useGlobalStorage();
    const { context } = useAnnotationLabelContext();
    const { request: pendingBoxRequest } = usePendingBoxClass();

    const CARD_TYPES: string[] = [
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.SEGMENTATION_MASK
    ];
    const selectedAnnotation = $derived(
        $isEditingMode && !context.isOnAnnotationDetailsView
            ? annotations.find(
                  (annotation) =>
                      annotation.sample_id === selectedAnnotationId &&
                      CARD_TYPES.includes(annotation.annotation_type)
              )
            : undefined
    );
</script>

{#if $pendingBoxRequest}
    <PendingBoxCard {collectionId} {getLayer} />
{:else if selectedAnnotation}
    {#key selectedAnnotation.sample_id}
        <AnnotationCard
            {collectionId}
            annotation={selectedAnnotation}
            {refetch}
            {getLayer}
            {colorBySource}
        />
    {/key}
{/if}
