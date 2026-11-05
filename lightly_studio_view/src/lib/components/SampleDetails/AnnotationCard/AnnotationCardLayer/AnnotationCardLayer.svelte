<script lang="ts">
    import { usePendingBoxClass } from '$lib/hooks';
    import { PendingBoxCard } from '../PendingBoxCard';

    // The cards over the canvas: the class picker of a drawn box. The card hides itself while
    // drawing.
    interface Props {
        /** The collection that owns the annotation classes. */
        collectionId: string;
        getLayer: () => SVGGraphicsElement | null;
    }

    const { collectionId, getLayer }: Props = $props();
    const { request: pendingBoxRequest } = usePendingBoxClass();
</script>

{#if $pendingBoxRequest}
    <PendingBoxCard {collectionId} {getLayer} />
{/if}
