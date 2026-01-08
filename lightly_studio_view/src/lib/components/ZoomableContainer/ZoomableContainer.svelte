<script lang="ts">
    import { select, selectAll } from 'd3-selection';
    import { zoom as D3zoom, zoomIdentity, type D3ZoomEvent, type ZoomBehavior } from 'd3-zoom';
    import { onMount, type Snippet } from 'svelte';
    import { unscale } from './unscale';
    import ZoomPanel from '$lib/components/ZoomPanel/ZoomPanel.svelte';

    let svgContainer: SVGSVGElement | null = $state(null);
    let svgContainerUnscaled: SVGSVGElement | null = $state(null);

    const {
        zoomableContent,
        boundingBox,
        width: containerWidth,
        height: containerHeight,
        cursor = 'auto',
        panEnabled = true,
        registerResetFn
    }: {
        width: number;
        height: number;
        cursor?: string;
        zoomableContent: Snippet<[{ scale: number }]>;
        // boundingBox is used to zoom in to the particular area
        boundingBox?: { x: number; y: number; width: number; height: number };
        registerResetFn?: (resetFn: () => void) => void;
        panEnabled?: boolean;
    } = $props();

    let svgElementWidth = $state(800);
    let svgElementHeight = $state(600);

    // Resize observer to update the SVG element size on window resize
    $effect(() => {
        if (!svgContainer) return;
        svgElementWidth = svgContainer.clientWidth;
        svgElementHeight = svgContainer.clientHeight;

        const resizeObserver = new ResizeObserver(() => {
            if (!svgContainer) return;
            svgElementWidth = svgContainer.clientWidth;
            svgElementHeight = svgContainer.clientHeight;
        });
        resizeObserver.observe(svgContainer);
        return () => resizeObserver.disconnect();
    });

    // Define the desired padding around the bounding box (in pixels)
    const SPACING = 10;

    const SVGViewBox = $derived.by(() => {
        // We can have selected annotation id from the page data to zoom in to the annotation
        const defaultViewBox = { x: 0, y: 0, width: containerWidth, height: containerHeight };

        if (boundingBox) {
            resetZoom();
            const { x, y, width, height } = boundingBox;
            return {
                x: Math.round(Math.max(0, x - SPACING)),
                y: Math.round(Math.max(0, y - SPACING)),
                width: Math.round(Math.min(containerWidth - x, width + SPACING * 2)),
                height: Math.round(Math.min(containerHeight - y, height + SPACING * 2))
            };
        }

        return defaultViewBox;
    });

    // Initial transform state
    // Note: x,y,k values are conventional names for d3-zoom https://d3js.org/d3-zoom#ZoomTransform
    let transform = $state({ k: 1, x: 0, y: 0 });

    // Calculate effective zoom that considers how the image fits in the container
    const effectiveZoom = $derived.by(() => {
        if (!svgContainer) return 1; // default to 100%

        // Calculate the initial scale to fit the image in the container
        const scaleX = svgElementWidth / containerWidth;
        const scaleY = svgElementHeight / containerHeight;
        const initialScale = Math.min(scaleX, scaleY);

        // The effective zoom is the current transform scale multiplied by the initial fit scale
        return transform.k * initialScale;
    });

    // Calculate complete scale factor including bounding box scaling
    const completeScale = $derived.by(() => {
        if (!svgContainer) return 1;

        // Start with the effective zoom (transform.k * initialScale)
        let scale = effectiveZoom;

        // If we have a bounding box, add the additional scaling from the viewBox change
        if (boundingBox) {
            const viewBoxScaleX = containerWidth / SVGViewBox.width;
            const viewBoxScaleY = containerHeight / SVGViewBox.height;
            const viewBoxScale = Math.min(viewBoxScaleX, viewBoxScaleY);
            scale *= viewBoxScale;
        }

        return scale;
    });

    type EventZoom = D3ZoomEvent<SVGSVGElement, unknown>;
    // Zoom behavior
    let zoom: ZoomBehavior<SVGSVGElement, unknown> | null = $state(null);
    const setupZoom = () => {
        if (!svgContainer) return;

        // we use d3-zoom to handle zooming and panning https://d3js.org/d3-zoom
        zoom = D3zoom<SVGSVGElement, unknown>()
            .on('zoom', (event: EventZoom) => {
                transform = event.transform;
            })
            .filter((event: MouseEvent | WheelEvent) => {
                if (!panEnabled) return false;
                // Allow wheel events, touch events, and mouse events (except right click)
                return (
                    (!event.ctrlKey || event.type === 'wheel') &&
                    !event.button &&
                    !(event.type === 'mousedown' && event.button === 2)
                );
            })
            .wheelDelta((event: WheelEvent) => {
                // Adjust wheel sensitivity, negative value to invert direction if needed
                return -event.deltaY * 0.002;
            });

        select(svgContainer).call(zoom).on('dblclick.zoom', null); // Disable double-click zoom
    };

    const handleZoom = (zoomIn: boolean) => {
        if (!svgContainer || !zoom) return;
        const scaleFactor = zoomIn ? 1.5 : 0.75;
        select(svgContainer).transition().duration(300).call(zoom.scaleBy, scaleFactor);
    };

    const resetZoom = () => {
        if (!svgContainer || !zoom) return;

        select(svgContainer).transition().duration(300).call(zoom.transform, zoomIdentity);
    };

    const resetTransform = () => {
        // Directly reset the transform state
        transform = { k: 1, x: 0, y: 0 };

        // Also reset the D3 zoom behavior if ready
        if (svgContainer && zoom) {
            select(svgContainer).call(zoom.transform, zoomIdentity);
        }
    };

    onMount(() => {
        setupZoom();
        registerResetFn?.(resetTransform);
    });

    $effect(() => {
        // we need to track "k" - to adjust the unscaled elements on zoom
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        transform.k;
        selectAll('.unscaled').each(function () {
            // we use reference to unscale the elements by svgContainerUnscaled
            unscale(this as SVGGraphicsElement, svgContainerUnscaled!);
        });
    });
</script>

<div class="relative flex h-full w-full select-none items-center justify-center">
    <ZoomPanel
        scale={effectiveZoom}
        onZoomIn={() => handleZoom(true)}
        onZoomOut={() => handleZoom(false)}
        onZoomReset={resetZoom}
    />
    <svg
        bind:this={svgContainer}
        class="z-10 h-full w-full"
        preserveAspectRatio="xMidYMid meet"
        style={`cursor: ${cursor};`}
        viewBox={`${SVGViewBox.x} ${SVGViewBox.y} ${SVGViewBox.width} ${SVGViewBox.height}`}
    >
        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
            {@render zoomableContent({ scale: completeScale })}
        </g>
    </svg>
    <!-- This is the unscaled SVG element that is used to have a reference for the unscaled elements -->
    <svg
        bind:this={svgContainerUnscaled}
        class="pointer-events-none absolute inset-0"
        viewBox={`0 0 1024 768`}
        preserveAspectRatio="xMidYMid meet"
    >
    </svg>
</div>
