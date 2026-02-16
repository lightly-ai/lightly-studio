<script lang="ts">
    import { select } from 'd3-selection';
    import { onMount, tick } from 'svelte';

    import { createResizeDrag } from './createResizeDrag';
    import { createMoveDrag } from './createMoveDrag';
    import type { BoundingBox } from '$lib/types';

    const {
        bbox = $bindable(),
        colorStroke = '#007bff',
        colorFill = 'transparent',
        opacity = 0.3,
        handleSize = 12,
        scale = 1,
        onResize,
        onMove,
        onDragEnd
    }: {
        bbox: BoundingBox;
        scale?: number;
        colorStroke?: string;
        colorFill?: string;
        opacity?: number;
        handleSize?: number;
        onResize?: (newBbox: BoundingBox) => void;
        onMove?: (newBbox: BoundingBox) => void;
        onDragEnd?: (newBbox: BoundingBox) => void;
    } = $props();

    const { x, y, width, height } = $derived(bbox);
    let svgGroup = $state<SVGGElement | undefined>();
    let isInteracting = $state(false);

    type Handle = {
        id: string;
        x: number;
        y: number;
        cursor: string;
        label: string;
    };
    function renderHandles() {
        if (!svgGroup) return;
        const scaledHandleSize = handleSize / scale;

        // Constrain handle size: minimum 3px for usability, maximum based on bbox size to prevent overlap
        const MIN_HANDLE_SIZE = 3;
        const MAX_HANDLE_SIZE = 7;
        const adaptiveHandleSize = Math.max(
            MIN_HANDLE_SIZE,
            Math.min(scaledHandleSize, width * 0.1, height * 0.1, MAX_HANDLE_SIZE)
        );
        const handles: Handle[] = [
            {
                id: 'nw',
                x: x - adaptiveHandleSize / 2,
                y: y - adaptiveHandleSize / 2,
                cursor: 'nwse-resize',
                label: 'Resize northwest corner'
            },
            {
                id: 'ne',
                x: x + width - adaptiveHandleSize / 2,
                y: y - adaptiveHandleSize / 2,
                cursor: 'nesw-resize',
                label: 'Resize northeast corner'
            },
            {
                id: 'sw',
                x: x - adaptiveHandleSize / 2,
                y: y + height - adaptiveHandleSize / 2,
                cursor: 'nesw-resize',
                label: 'Resize southwest corner'
            },
            {
                id: 'se',
                x: x + width - adaptiveHandleSize / 2,
                y: y + height - adaptiveHandleSize / 2,
                cursor: 'nwse-resize',
                label: 'Resize southeast corner'
            },
            {
                id: 'n',
                x: x + width / 2 - adaptiveHandleSize / 2,
                y: y - adaptiveHandleSize / 2,
                cursor: 'ns-resize',
                label: 'Resize top edge'
            },
            {
                id: 's',
                x: x + width / 2 - adaptiveHandleSize / 2,
                y: y + height - adaptiveHandleSize / 2,
                cursor: 'ns-resize',
                label: 'Resize bottom edge'
            },
            {
                id: 'w',
                x: x - adaptiveHandleSize / 2,
                y: y + height / 2 - adaptiveHandleSize / 2,
                cursor: 'ew-resize',
                label: 'Resize left edge'
            },
            {
                id: 'e',
                x: x + width - adaptiveHandleSize / 2,
                y: y + height / 2 - adaptiveHandleSize / 2,
                cursor: 'ew-resize',
                label: 'Resize right edge'
            }
        ];

        const selection = select(svgGroup);

        // @ts-expect-error there is a type issue in d3's types
        const handleSelection = selection.selectAll('.resize-handle').data(handles, (d) => d.id);

        handleSelection
            .enter()
            .append('rect')
            .attr('class', 'resize-handle')
            .attr('width', adaptiveHandleSize)
            .attr('height', adaptiveHandleSize)
            .attr('fill', colorStroke)
            .attr('stroke', colorStroke)
            .attr('stroke-width', '1')
            .attr('vector-effect', 'non-scaling-stroke')
            .attr('role', 'button')
            .attr('style', (d) => `cursor: ${d.cursor};`)
            .attr('data-testid', (d) => `resize-handle-${d.id}`)
            .attr('aria-label', (d) => d.label)
            // @ts-expect-error there is a type issue in d3's types
            .merge(handleSelection)
            .attr('x', (d) => d.x)
            .attr('y', (d) => d.y)
            .attr('width', adaptiveHandleSize)
            .attr('height', adaptiveHandleSize)
            .attr('fill', colorStroke)
            .attr('stroke', colorStroke);

        handleSelection.exit().remove();
    }

    function setupResizeHandles() {
        if (!svgGroup) return;

        const handles = ['nw', 'ne', 'sw', 'se', 'n', 's', 'w', 'e'];
        handles.forEach((handle) => {
            if (!svgGroup) return;
            const element = svgGroup.querySelector(`[data-testid="resize-handle-${handle}"]`);
            if (element) {
                select(element).call(
                    createResizeDrag({
                        handle,
                        getCurrentBbox: () => ({ x, y, width, height }),
                        onResize: (newBoundingBox) => {
                            bbox.x = newBoundingBox.x;
                            bbox.y = newBoundingBox.y;
                            bbox.width = newBoundingBox.width;
                            bbox.height = newBoundingBox.height;

                            if (onResize) {
                                onResize(newBoundingBox);
                            }

                            renderHandles();
                        },
                        onDragEnd: (newBoundingBox) => {
                            if (onDragEnd) {
                                onDragEnd(newBoundingBox);
                            }
                        },
                        onInteractionStart: () => {
                            isInteracting = true;
                        },
                        onInteractionEnd: () => {
                            isInteracting = false;
                        }
                    })
                );
            }
        });

        // Setup move handle
        const moveElement = svgGroup.querySelector(`.movable-rectangle`);
        if (moveElement) {
            select(moveElement).call(
                createMoveDrag({
                    getCurrentBbox: () => ({ x, y, width, height }),
                    onMove: (newBoundingBox) => {
                        bbox.x = newBoundingBox.x;
                        bbox.y = newBoundingBox.y;
                        bbox.width = newBoundingBox.width;
                        bbox.height = newBoundingBox.height;

                        if (onMove) {
                            onMove(newBoundingBox);
                        }

                        renderHandles();
                    },
                    onDragEnd: (newBoundingBox) => {
                        if (onDragEnd) {
                            onDragEnd(newBoundingBox);
                        }
                    },
                    onInteractionStart: () => {
                        isInteracting = true;
                    },
                    onInteractionEnd: () => {
                        isInteracting = false;
                    }
                })
            );
        }
    }

    onMount(() => {
        if (svgGroup) {
            renderHandles();
            setupResizeHandles();
        }
    });

    const init = async () => {
        if (svgGroup) {
            await tick();
            renderHandles();
            setupResizeHandles();
        }
    };
    $effect(() => {
        renderHandles();
        init();
    });
</script>

<g bind:this={svgGroup}>
    <rect
        {x}
        {y}
        {width}
        {height}
        stroke={colorStroke}
        stroke-width="2"
        fill={colorFill}
        fill-opacity={opacity}
        pointer-events="all"
        vector-effect="non-scaling-stroke"
        class="movable-rectangle"
        data-testid="annotation_box"
        style="cursor: move;"
    />
    {#if isInteracting}
        <text
            x={x - 10 / scale}
            y={y + 1 / scale}
            dominant-baseline="middle"
            fill={colorStroke}
            font-size={14 / scale}
            text-anchor="end"
        >
            x: {x}, y: {y}
        </text>
        <text
            x={x + width / 2}
            y={y + height + 20 / scale}
            fill={colorStroke}
            font-size={14 / scale}
            text-anchor="middle"
        >
            w: {width}px
        </text>
        <text
            x={x - 10 / scale}
            y={y + height / 2}
            dominant-baseline="middle"
            fill={colorStroke}
            font-size={14 / scale}
            text-anchor="end"
        >
            h: {height}px
        </text>
    {/if}
</g>
