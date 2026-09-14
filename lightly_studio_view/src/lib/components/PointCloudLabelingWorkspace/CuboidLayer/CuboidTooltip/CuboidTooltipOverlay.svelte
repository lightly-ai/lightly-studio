<script lang="ts">
    import type {
        AnnotationClass,
        CuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidTooltip from './CuboidTooltip.svelte';

    /**
     * Cursor-following overlay that renders CuboidTooltip outside the Threlte canvas.
     * Position the overlay as `absolute inset-0` over the viewport container.
     */
    interface Props {
        /** Cursor X position in pixels, relative to the overlay element. */
        cursorX: number;
        /** Cursor Y position in pixels, relative to the overlay element. */
        cursorY: number;
        /** Identity of the currently hovered cuboid, or null. */
        hoveredAnnotationId: string | null;
        /** All cuboids in the scene — used to look up the hovered one. */
        cuboids: readonly CuboidAnnotation[];
        /** Annotation classes — used to resolve the hovered cuboid's display name. */
        annotationClasses: readonly AnnotationClass[];
    }

    const TOOLTIP_OFFSET_PX = 12;
    const HOVER_DELAY_MS = 100;

    let { cursorX, cursorY, hoveredAnnotationId, cuboids, annotationClasses }: Props = $props();

    let overlayEl = $state<HTMLDivElement | undefined>(undefined);
    let tooltipEl = $state<HTMLDivElement | undefined>(undefined);
    let showTooltip = $state(false);
    let hoverTimer: ReturnType<typeof setTimeout> | undefined;

    const hoveredCuboid = $derived(cuboids.find((c) => c.id === hoveredAnnotationId) ?? null);

    const hoveredAnnotationClassName = $derived(
        hoveredCuboid
            ? (annotationClasses.find(({ id }) => id === hoveredCuboid.annotationClassId)?.name ??
                  hoveredCuboid.annotationClassId)
            : ''
    );

    $effect(() => {
        if (hoveredAnnotationId) {
            hoverTimer = setTimeout(() => {
                showTooltip = true;
            }, HOVER_DELAY_MS);
        } else {
            clearTimeout(hoverTimer);
            showTooltip = false;
        }
        return () => clearTimeout(hoverTimer);
    });

    const tooltipX = $derived.by(() => {
        const containerW = overlayEl?.offsetWidth ?? 0;
        const tooltipW = tooltipEl?.offsetWidth ?? 260;
        return cursorX + TOOLTIP_OFFSET_PX + tooltipW > containerW
            ? cursorX - TOOLTIP_OFFSET_PX - tooltipW
            : cursorX + TOOLTIP_OFFSET_PX;
    });

    const tooltipY = $derived.by(() => {
        const containerH = overlayEl?.offsetHeight ?? 0;
        const tooltipH = tooltipEl?.offsetHeight ?? 200;
        return cursorY + TOOLTIP_OFFSET_PX + tooltipH > containerH
            ? cursorY - TOOLTIP_OFFSET_PX - tooltipH
            : cursorY + TOOLTIP_OFFSET_PX;
    });
</script>

<div bind:this={overlayEl} class="pointer-events-none absolute inset-0 z-50">
    {#if hoveredCuboid}
        <div
            bind:this={tooltipEl}
            class="absolute"
            class:invisible={!showTooltip}
            style="left: {tooltipX}px; top: {tooltipY}px;"
        >
            <CuboidTooltip
                annotation={hoveredCuboid}
                annotationClassName={hoveredAnnotationClassName}
            />
        </div>
    {/if}
</div>
