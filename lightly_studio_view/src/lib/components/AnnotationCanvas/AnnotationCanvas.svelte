<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { getColorByLabel } from '$lib/utils';
    import type { BoundingBox } from '$lib/types';

    type SegmentationAnnotation = {
        annotation_type: 'semantic_segmentation';
        annotation_label_name: string;
        segmentation_mask?: number[] | null;
        object_detection_details?: undefined;
    };

    type InstanceAnnotation = {
        annotation_type: 'instance_segmentation';
        annotation_label_name: string;
        segmentation_mask?: number[] | null;
        object_detection_details?: BoundingBox;
    };

    type ObjectDetectionAnnotation = {
        annotation_type: 'object_detection';
        annotation_label_name: string;
        object_detection_details: BoundingBox;
        segmentation_mask?: undefined;
    };

    type AnnotationCanvasAnnotation =
        | SegmentationAnnotation
        | InstanceAnnotation
        | ObjectDetectionAnnotation;

    const {
        width,
        height,
        annotations = [],
        alpha = 0.4,
        className = ''
    }: {
        width: number;
        height: number;
        annotations?: AnnotationCanvasAnnotation[];
        alpha?: number;
        className?: string;
    } = $props();

    let canvasEl: HTMLCanvasElement | null = null;
    let worker: Worker | null = null;
    let workerReady = false;
    let hasOffscreen = false;
    let resizeObserver: ResizeObserver | null = null;

    type ColorParser = (color: string) => [number, number, number, number];

    const createColorParser = (): ColorParser => {
        if (typeof document === 'undefined') {
            return () => [0, 0, 0, 0];
        }

        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        const ctx = canvas.getContext('2d');

        return (color: string) => {
            if (!ctx) {
                return [0, 0, 0, 0];
            }

            ctx.clearRect(0, 0, 1, 1);
            ctx.fillStyle = color;
            ctx.fillRect(0, 0, 1, 1);
            const data = ctx.getImageData(0, 0, 1, 1).data;
            return [data[0], data[1], data[2], data[3]];
        };
    };

    let rgbaParser: ColorParser = () => [0, 0, 0, 0];

    type MaskPayload = { rle: number[]; color: [number, number, number, number] };
    type BoxPayload = {
        x: number;
        y: number;
        width: number;
        height: number;
        color: [number, number, number, number];
    };

    const normalizeRLE = (mask?: ArrayLike<number> | null): number[] => {
        if (!mask?.length) {
            return [];
        }

        // Convert to a plain number array so Worker.postMessage can structured-clone it.
        return Array.from(mask, (value) => Number(value) || 0);
    };

    // Collect mask RLEs and any available bounding boxes in image space.
    const buildRenderPayload = (): { masks: MaskPayload[]; boxes: BoxPayload[] } => {
        const masks: MaskPayload[] = [];
        const boxes: BoxPayload[] = [];

        for (const annotation of annotations) {
            const labelName = annotation.annotation_label_name || 'label';

            const rle = normalizeRLE(annotation.segmentation_mask);
            if (rle.length) {
                masks.push({
                    rle,
                    color: rgbaParser(getColorByLabel(labelName, alpha).color)
                });
            }

            const bbox = annotation.object_detection_details;
            if (bbox) {
                boxes.push({
                    x: Math.round(bbox.x),
                    y: Math.round(bbox.y),
                    width: Math.round(bbox.width),
                    height: Math.round(bbox.height),
                    color: rgbaParser(getColorByLabel(labelName, 1).color)
                });
            }
        }

        return { masks, boxes };
    };

    const render = () => {
        if (!worker || !workerReady) {
            return;
        }

        // Clear fallback canvas path to avoid stale pixels before new draw arrives.
        if (!hasOffscreen && canvasEl) {
            const ctx = canvasEl.getContext('2d');
            ctx?.clearRect(0, 0, width, height);
        }

        // Include current CSS scale so the worker can keep stroke widths consistent.
        const scaleX = canvasEl && width ? canvasEl.clientWidth / width : 1;
        const scaleY = canvasEl && height ? canvasEl.clientHeight / height : 1;

        worker.postMessage({
            type: 'render',
            width,
            height,
            scaleX,
            scaleY,
            ...buildRenderPayload()
        });
    };

    const setupWorker = () => {
        if (!canvasEl) {
            return;
        }

        worker = new Worker(new URL('../../workers/maskRenderer.worker.ts', import.meta.url), {
            type: 'module'
        });

        worker.onmessage = (event: MessageEvent) => {
            if (event.data?.type !== 'image' || !canvasEl) {
                return;
            }

            const {
                width: w,
                height: h,
                data,
                boxes = [],
                stroke = 2
            } = event.data as {
                width: number;
                height: number;
                data: Uint8ClampedArray;
                boxes?: BoxPayload[];
                stroke?: number;
            };

            const ctx = canvasEl.getContext('2d', { willReadFrequently: true });
            if (!ctx) {
                return;
            }

            const imageData = new ImageData(new Uint8ClampedArray(data), w, h);
            ctx.putImageData(imageData, 0, 0);

            if (boxes.length) {
                ctx.save();
                ctx.lineWidth = stroke;
                const clamp = (value: number, min: number, max: number) =>
                    Math.min(Math.max(value, min), max);

                for (const box of boxes) {
                    ctx.strokeStyle = `rgba(${box.color[0]}, ${box.color[1]}, ${box.color[2]}, ${
                        box.color[3] / 255
                    })`;
                    const x = clamp(box.x, 0, w);
                    const y = clamp(box.y, 0, h);
                    const wBox = clamp(box.width, 0, w - x);
                    const hBox = clamp(box.height, 0, h - y);

                    if (wBox === 0 || hBox === 0) {
                        continue;
                    }

                    ctx.strokeRect(x, y, wBox, hBox);
                }

                ctx.restore();
            }
        };

        if (canvasEl.transferControlToOffscreen) {
            const offscreen = canvasEl.transferControlToOffscreen();
            worker.postMessage({ type: 'init', canvas: offscreen }, [offscreen]);
            hasOffscreen = true;
        } else {
            hasOffscreen = false;
        }

        workerReady = true;
        render();
    };

    onMount(() => {
        rgbaParser = createColorParser();
        setupWorker();

        if (canvasEl && 'ResizeObserver' in window) {
            resizeObserver = new ResizeObserver(() => render());
            resizeObserver.observe(canvasEl);
        }
    });

    onDestroy(() => {
        worker?.terminate();
        resizeObserver?.disconnect();
    });

    $effect(() => {
        if (workerReady) {
            render();
        }
    });
</script>

<canvas bind:this={canvasEl} {width} {height} class={className}></canvas>

<style>
    canvas {
        display: block;
    }
</style>
