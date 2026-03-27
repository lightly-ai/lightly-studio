<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { useCustomLabelColors, type CustomColor } from '$lib/hooks/useCustomLabelColors';
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

    const { customLabelColorsStore } = useCustomLabelColors();

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

    type CustomLabelColorMap = Record<string, CustomColor>;

    const clampAlpha = (value: number): number => Math.max(0, Math.min(value, 1));

    const resolveLabelColor = (
        labelName: string,
        colorAlpha: number,
        customLabelColors: CustomLabelColorMap
    ): [number, number, number, number] => {
        const customColor = customLabelColors[labelName];
        if (!customColor) {
            return rgbaParser(getColorByLabel(labelName, colorAlpha).color);
        }

        const [r, g, b] = rgbaParser(customColor.color);
        const alphaValue = Math.round(clampAlpha(customColor.alpha * colorAlpha) * 255);
        return [r, g, b, alphaValue];
    };

    const normalizeRLE = (mask?: ArrayLike<number> | null): number[] => {
        if (!mask?.length) {
            return [];
        }

        // Convert to a plain number array so Worker.postMessage can structured-clone it.
        return Array.from(mask, (value) => Number(value) || 0);
    };

    // Collect mask RLEs and any available bounding boxes in image space.
    const buildRenderPayload = (
        customLabelColors: CustomLabelColorMap
    ): { masks: MaskPayload[]; boxes: BoxPayload[] } => {
        const masks: MaskPayload[] = [];
        const boxes: BoxPayload[] = [];

        for (const annotation of annotations) {
            const labelName = annotation.annotation_label_name || 'label';

            const rle = normalizeRLE(annotation.segmentation_mask);
            if (rle.length) {
                masks.push({
                    rle,
                    color: resolveLabelColor(labelName, alpha, customLabelColors)
                });
            }

            const bbox = annotation.object_detection_details;
            if (bbox) {
                boxes.push({
                    x: Math.round(bbox.x),
                    y: Math.round(bbox.y),
                    width: Math.round(bbox.width),
                    height: Math.round(bbox.height),
                    color: resolveLabelColor(labelName, 1, customLabelColors)
                });
            }
        }

        return { masks, boxes };
    };

    const drawBoxes = (
        ctx: CanvasRenderingContext2D,
        boxes: BoxPayload[],
        canvasWidth: number,
        canvasHeight: number,
        stroke: number
    ) => {
        if (!boxes.length) {
            return;
        }

        ctx.save();
        ctx.lineWidth = stroke;
        const clamp = (value: number, min: number, max: number) =>
            Math.min(Math.max(value, min), max);

        for (const box of boxes) {
            ctx.strokeStyle = `rgba(${box.color[0]}, ${box.color[1]}, ${box.color[2]}, ${
                box.color[3] / 255
            })`;
            const x = clamp(box.x, 0, canvasWidth);
            const y = clamp(box.y, 0, canvasHeight);
            const wBox = clamp(box.width, 0, canvasWidth - x);
            const hBox = clamp(box.height, 0, canvasHeight - y);

            if (wBox === 0 || hBox === 0) {
                continue;
            }

            ctx.strokeRect(x, y, wBox, hBox);
        }

        ctx.restore();
    };

    const render = (customLabelColors: CustomLabelColorMap = $customLabelColorsStore) => {
        const payload = buildRenderPayload(customLabelColors);
        const scaleX = canvasEl && width ? canvasEl.clientWidth / width : 1;
        const scaleY = canvasEl && height ? canvasEl.clientHeight / height : 1;

        if (!workerReady && payload.masks.length === 0) {
            if (!canvasEl) {
                return;
            }

            const ctx = canvasEl.getContext('2d', { willReadFrequently: true });
            if (!ctx) {
                return;
            }

            ctx.clearRect(0, 0, width, height);
            if (!payload.boxes.length) {
                return;
            }

            const scale = Math.max(scaleX, scaleY) || 1;
            drawBoxes(ctx, payload.boxes, width, height, 2 / scale);
            return;
        }

        if (!workerReady) {
            setupWorker();
        }

        if (!worker || !workerReady) {
            return;
        }

        // Clear fallback canvas path to avoid stale pixels before new draw arrives.
        if (!hasOffscreen && canvasEl) {
            const ctx = canvasEl.getContext('2d');
            ctx?.clearRect(0, 0, width, height);
        }

        // Include current CSS scale so the worker can keep stroke widths consistent.
        worker.postMessage({
            type: 'render',
            width,
            height,
            scaleX,
            scaleY,
            ...payload
        });
    };

    const setupWorker = () => {
        if (!canvasEl || worker) {
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
            drawBoxes(ctx, boxes, w, h, stroke);
        };

        if (canvasEl.transferControlToOffscreen) {
            try {
                const offscreen = canvasEl.transferControlToOffscreen();
                worker.postMessage({ type: 'init', canvas: offscreen }, [offscreen]);
                hasOffscreen = true;
            } catch {
                // The canvas may already have a 2D context; keep worker in image-data fallback mode.
                hasOffscreen = false;
            }
        } else {
            hasOffscreen = false;
        }

        workerReady = true;
    };

    onMount(() => {
        rgbaParser = createColorParser();

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
        const customLabelColors = $customLabelColorsStore;
        render(customLabelColors);
    });
</script>

<canvas bind:this={canvasEl} {width} {height} class={className}></canvas>

<style>
    canvas {
        display: block;
    }
</style>
