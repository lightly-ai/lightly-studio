<script lang="ts">
    import { untrack, type Snippet } from 'svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import type { BoundingBox } from '$lib/types';
    import { imageRectToScreen, placePanel } from './annotationCard.helpers';

    interface Props {
        /** The annotation's rectangle in image coordinates. */
        bbox: BoundingBox;
        /** The annotation layer of the canvas, whose screen matrix includes pan and zoom. */
        getLayer: () => SVGGraphicsElement | null;
        testId: string;
        /** Runs each time the card becomes visible. A hidden card can't take focus. */
        onShow?: () => void;
        children: Snippet;
    }

    const { bbox, getLayer, testId, onShow, children }: Props = $props();
    const { isHidden } = useHideAnnotations();
    const { context: annotationLabelContext } = useAnnotationLabelContext();

    let panel: HTMLDivElement | undefined = $state();
    let position = $state<{ left: number; top: number } | null>(null);
    // Stays mounted while hidden, so text typed into the card survives.
    const isVisible = $derived(
        position !== null && !$isHidden && !annotationLabelContext.isDrawing
    );

    $effect(() => {
        if (isVisible) untrack(() => onShow?.());
    });

    // Follow the annotation on screen. Pan, zoom and edits all move it, so place the card every
    // frame instead of listening to each of them.
    $effect(() => {
        let last = '';
        let frame = 0;
        const update = () => {
            const layer = getLayer();
            const matrix = layer?.getScreenCTM();
            const canvas = layer?.ownerSVGElement;
            const next =
                matrix && canvas && panel
                    ? placePanel({
                          box: imageRectToScreen(bbox, matrix),
                          canvas: canvas.getBoundingClientRect(),
                          panel: { width: panel.offsetWidth, height: panel.offsetHeight }
                      })
                    : null;
            const key = JSON.stringify(next);
            if (key !== last) {
                last = key;
                position = next;
            }
            frame = requestAnimationFrame(update);
        };
        frame = requestAnimationFrame(update);
        return () => cancelAnimationFrame(frame);
    });
</script>

<div
    bind:this={panel}
    class="fixed z-20 flex w-60 flex-col gap-1.5 rounded-lg border bg-popover p-1.5 text-sm text-popover-foreground shadow-lg"
    style:left="{position?.left ?? 0}px"
    style:top="{position?.top ?? 0}px"
    style:visibility={isVisible ? 'visible' : 'hidden'}
    data-testid={testId}
>
    {@render children()}
</div>
