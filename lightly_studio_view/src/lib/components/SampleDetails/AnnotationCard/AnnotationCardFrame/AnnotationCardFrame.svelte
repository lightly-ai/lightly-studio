<script lang="ts">
    import { untrack, type Snippet } from 'svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { cn } from '$lib/utils';
    import type { BoundingBox } from '$lib/types';
    import { useCardPlacement } from './useCardPlacement.svelte';

    interface Props {
        /** The annotation's rectangle in image coordinates. */
        bbox: BoundingBox;
        /** The annotation layer of the canvas, whose screen matrix includes pan and zoom. */
        getLayer: () => SVGGraphicsElement | null;
        /** The accessible name of the card. */
        label: string;
        testId: string;
        /** Whether the card is shown, so its keys may act. Bind to read it. */
        isActive?: boolean;
        /** Runs each time the card becomes visible. A hidden card can't take focus. */
        onShow?: (card: HTMLElement) => void;
        /** A pointer press anywhere outside the card. */
        onPointerDownOutside?: (event: PointerEvent) => void;
        children: Snippet;
    }

    let {
        bbox,
        getLayer,
        label,
        testId,
        isActive = $bindable(false),
        onShow,
        onPointerDownOutside,
        children
    }: Props = $props();
    const { isHidden } = useHideAnnotations();
    const { context: annotationLabelContext } = useAnnotationLabelContext();

    let panel: HTMLDivElement | undefined = $state();
    const placement = useCardPlacement(() => ({ bbox, layer: getLayer(), card: panel }));
    // Stays mounted while hidden, so text typed into the card survives. A box panned off the
    // canvas hides the card too, instead of leaving it at the canvas edge.
    const isVisible = $derived(
        placement.current !== null &&
            placement.current.isBoxOnCanvas &&
            !$isHidden &&
            !annotationLabelContext.isDrawing &&
            !annotationLabelContext.isMovingAnnotation
    );

    $effect(() => {
        isActive = isVisible;
    });
    $effect(() => {
        const card = panel;
        if (isVisible && card) untrack(() => onShow?.(card));
    });

    const handleWindowPointerDown = (event: PointerEvent) => {
        if (!onPointerDownOutside) return;
        if (event.target instanceof Node && panel?.contains(event.target)) return;
        onPointerDownOutside(event);
    };
</script>

<svelte:window onpointerdown={handleWindowPointerDown} />

<!-- Fades instead of blinking. Visibility flips at the end of a fade-out and at the start of a
     fade-in, so a hidden card takes no clicks and a shown card can take focus at once. -->
<div
    bind:this={panel}
    role="group"
    aria-label={label}
    class={cn(
        'fixed z-20 flex w-60 flex-col gap-1.5 rounded-lg border bg-popover p-1.5 text-sm text-popover-foreground shadow-lg transition-[opacity,visibility] duration-100',
        !isVisible && 'pointer-events-none'
    )}
    style:left="{placement.current?.left ?? 0}px"
    style:top="{placement.current?.top ?? 0}px"
    style:opacity={isVisible ? 1 : 0}
    style:visibility={isVisible ? 'visible' : 'hidden'}
    data-testid={testId}
    data-annotation-card
>
    {@render children()}
</div>
