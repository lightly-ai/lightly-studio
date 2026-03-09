<script lang="ts">
    import { select, selectAll } from 'd3-selection';
    import 'd3-transition';
    import { zoom as D3zoom, zoomIdentity, type D3ZoomEvent, type ZoomBehavior } from 'd3-zoom';
    import { onMount, type Snippet } from 'svelte';
    import { unscale } from './unscale';
    import ZoomPanel from '../ZoomPanel/ZoomPanel.svelte';

    let svgContainer: SVGSVGElement | null = $state(null);
    let svgContainerUnscaled: SVGSVGElement | null = $state(null);

    const {
        zoomableContent,
        boundingBox,
        autoFocusEnabled = true,
        autoFocusKey,
        width: containerWidth,
        height: containerHeight,
        cursor = 'auto',
        panEnabled = true,
        zoomEnabled = true,
        toolbarContent,
        registerResetFn,
        zoomPanelContent
    }: {
        width: number;
        height: number;
        cursor?: string;
        zoomableContent: Snippet<[{ scale: number }]>;
        // boundingBox is used to zoom in to the particular area
        boundingBox?: { x: number; y: number; width: number; height: number };
        autoFocusEnabled?: boolean;
        autoFocusKey?: string | undefined;
        registerResetFn?: (resetFn: () => void) => void;
        panEnabled?: boolean;
        zoomEnabled?: boolean;
        toolbarContent?: Snippet;
        zoomPanelContent?: Snippet;
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

    let activeFocusedBoundingBox = $state<
        { x: number; y: number; width: number; height: number } | undefined
    >(undefined);
    let resetTargetBoundingBox = $state<
        { x: number; y: number; width: number; height: number } | undefined
    >(undefined);
    let focusedBoundingBoxKey = $state<string | undefined>(undefined);

    $effect(() => {
        if (!autoFocusEnabled || !boundingBox) return;

        const nextFocusKey =
            autoFocusKey ??
            `${Math.round(boundingBox.x)}:${Math.round(boundingBox.y)}:${Math.round(boundingBox.width)}:${Math.round(boundingBox.height)}`;
        if (focusedBoundingBoxKey === nextFocusKey) {
            // Keep reset target in sync without changing the active view.
            resetTargetBoundingBox = boundingBox;
            return;
        }

        activeFocusedBoundingBox = boundingBox;
        resetTargetBoundingBox = boundingBox;
        focusedBoundingBoxKey = nextFocusKey;
        resetZoom();
    });

    $effect(() => {
        if (!autoFocusEnabled) return;
        if (boundingBox) return;
        // Keep the last focused box while data is temporarily unavailable (e.g. during refetch)
        // if a stable focus key is provided by the caller.
        if (autoFocusKey) return;

        activeFocusedBoundingBox = undefined;
        resetTargetBoundingBox = undefined;
        focusedBoundingBoxKey = undefined;
    });

    const SVGViewBox = $derived.by(() => {
        // We can have selected annotation id from the page data to zoom in to the annotation
        const defaultViewBox = { x: 0, y: 0, width: containerWidth, height: containerHeight };

        if (activeFocusedBoundingBox) {
            const { x, y, width, height } = activeFocusedBoundingBox;
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
        if (activeFocusedBoundingBox) {
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
                if (!zoomEnabled) return;
                transform = event.transform;
            })
            .filter((event: MouseEvent | WheelEvent) => {
                if (!panEnabled || !zoomEnabled) return false;
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

    const handleZoomReset = () => {
        if (resetTargetBoundingBox) {
            activeFocusedBoundingBox = resetTargetBoundingBox;
        }
        resetZoom();
    };

    const resetTransform = () => {
        // Directly reset the transform state
        transform = { k: 1, x: 0, y: 0 };

        // Also reset the D3 zoom behavior if ready
        if (svgContainer && zoom) {
            select(svgContainer).call(zoom.transform, zoomIdentity);
        }
    };

    const MOVEMENT_KEY_CODES = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD']);
    const KEYBOARD_PAN_SPEED_PX_PER_SECOND = 600;

    let pressedMovementKeys = new Set<string>();
    let isSpacePanActive = false;
    let isKeyboardPanContextActive = false;
    let keyboardPanAnimationFrameId: number | null = null;

    const isTextInputTarget = (target: EventTarget | null) => {
        if (!(target instanceof HTMLElement)) return false;
        return (
            target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable
        );
    };

    const stopKeyboardPanLoop = () => {
        if (keyboardPanAnimationFrameId === null) return;
        cancelAnimationFrame(keyboardPanAnimationFrameId);
        keyboardPanAnimationFrameId = null;
    };

    const resetKeyboardPanState = () => {
        pressedMovementKeys.clear();
        isSpacePanActive = false;
        stopKeyboardPanLoop();
    };

    const getKeyboardPanDirection = () => {
        let x = 0;
        let y = 0;

        // W/A/S/D move the viewport like game controls.
        if (pressedMovementKeys.has('KeyW')) y += 1;
        if (pressedMovementKeys.has('KeyS')) y -= 1;
        if (pressedMovementKeys.has('KeyA')) x += 1;
        if (pressedMovementKeys.has('KeyD')) x -= 1;

        if (x !== 0 && y !== 0) {
            x *= Math.SQRT1_2;
            y *= Math.SQRT1_2;
        }

        return { x, y };
    };

    const panWithKeyboard = (elapsedSeconds: number) => {
        if (!svgContainer || !zoom) return false;

        const direction = getKeyboardPanDirection();
        if (direction.x === 0 && direction.y === 0) {
            return false;
        }

        const panDistance = KEYBOARD_PAN_SPEED_PX_PER_SECOND * elapsedSeconds;
        select(svgContainer).call(
            zoom.translateBy,
            (direction.x * panDistance) / transform.k,
            (direction.y * panDistance) / transform.k
        );

        return true;
    };

    const ensureKeyboardPanLoop = () => {
        if (keyboardPanAnimationFrameId !== null) return;
        let previousFrameTimestamp: number | null = null;

        const onKeyboardPanFrame = (timestamp: number) => {
            if (
                !svgContainer ||
                !zoom ||
                !panEnabled ||
                !zoomEnabled ||
                !isSpacePanActive ||
                pressedMovementKeys.size === 0
            ) {
                stopKeyboardPanLoop();
                return;
            }

            const elapsedSeconds =
                previousFrameTimestamp === null
                    ? 1 / 60
                    : (timestamp - previousFrameTimestamp) / 1000;
            previousFrameTimestamp = timestamp;

            const didPan = panWithKeyboard(elapsedSeconds);
            if (!didPan) {
                stopKeyboardPanLoop();
                return;
            }

            keyboardPanAnimationFrameId = requestAnimationFrame(onKeyboardPanFrame);
        };

        keyboardPanAnimationFrameId = requestAnimationFrame(onKeyboardPanFrame);
    };

    const handleContainerKeyDown = (event: KeyboardEvent) => {
        if (!isKeyboardPanContextActive) return;
        if (!panEnabled || !zoomEnabled) return;
        if (isTextInputTarget(event.target)) return;

        if (event.code === 'Space') {
            isSpacePanActive = true;
            event.preventDefault();
            if (pressedMovementKeys.size > 0) {
                panWithKeyboard(1 / 60);
                ensureKeyboardPanLoop();
            }
            return;
        }

        if (!MOVEMENT_KEY_CODES.has(event.code)) return;

        pressedMovementKeys.add(event.code);
        if (!isSpacePanActive) return;

        event.preventDefault();
        panWithKeyboard(1 / 60);
        ensureKeyboardPanLoop();
    };

    const handleContainerKeyUp = (event: KeyboardEvent) => {
        if (event.code === 'Space') {
            isSpacePanActive = false;
            stopKeyboardPanLoop();
            return;
        }

        if (!MOVEMENT_KEY_CODES.has(event.code)) return;
        pressedMovementKeys.delete(event.code);

        if (pressedMovementKeys.size === 0) {
            stopKeyboardPanLoop();
        }
    };

    const handleContainerMouseEnter = () => {
        isKeyboardPanContextActive = true;
    };

    const handleContainerMouseLeave = () => {
        isKeyboardPanContextActive = false;
        resetKeyboardPanState();
    };

    const handleWindowMouseDown = (event: MouseEvent) => {
        if (!(event.target instanceof Node)) return;
        if (svgContainer?.contains(event.target)) return;

        isKeyboardPanContextActive = false;
        resetKeyboardPanState();
    };

    const handleWindowBlur = () => {
        resetKeyboardPanState();
        isKeyboardPanContextActive = false;
    };

    onMount(() => {
        setupZoom();
        registerResetFn?.(resetTransform);

        if (!svgContainer) return;
        const zoomableElement = svgContainer;

        zoomableElement.addEventListener('mouseenter', handleContainerMouseEnter);
        zoomableElement.addEventListener('mouseleave', handleContainerMouseLeave);
        window.addEventListener('keydown', handleContainerKeyDown);
        window.addEventListener('keyup', handleContainerKeyUp);
        window.addEventListener('mousedown', handleWindowMouseDown);
        window.addEventListener('blur', handleWindowBlur);

        return () => {
            stopKeyboardPanLoop();
            zoomableElement.removeEventListener('mouseenter', handleContainerMouseEnter);
            zoomableElement.removeEventListener('mouseleave', handleContainerMouseLeave);
            window.removeEventListener('keydown', handleContainerKeyDown);
            window.removeEventListener('keyup', handleContainerKeyUp);
            window.removeEventListener('mousedown', handleWindowMouseDown);
            window.removeEventListener('blur', handleWindowBlur);
        };
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
    {#if toolbarContent}
        {@render toolbarContent()}
    {/if}

    <ZoomPanel
        scale={effectiveZoom}
        onZoomIn={() => handleZoom(true)}
        onZoomOut={() => handleZoom(false)}
        onZoomReset={handleZoomReset}
    >
        {#snippet content()}
            {#if zoomPanelContent}
                {@render zoomPanelContent()}
            {/if}
        {/snippet}
    </ZoomPanel>
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
