<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    interface Props {
        isPending?: boolean;
    }

    const { isPending = false }: Props = $props();
    const { context, setAnnotationId, setLastCreatedAnnotationId } = useAnnotationLabelContext();

    const finish = () => {
        // Strokes save on pointerup; deselecting starts a new object on the next stroke.
        setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };
</script>

{#if !context.isOnAnnotationDetailsView}
    <div class="grid">
        <Button
            size="xs"
            aria-label="Finish"
            disabled={!context.annotationId || context.isDrawing || isPending}
            onclick={finish}>Finish</Button
        >
    </div>
{/if}
