<script module lang="ts">
    let annotationCanvasInstanceCounter = 0;

    const createCanvasInstanceSuffix = (): string => {
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
            return crypto.randomUUID();
        }

        const fallbackSuffix = annotationCanvasInstanceCounter;
        annotationCanvasInstanceCounter += 1;
        return String(fallbackSuffix);
    };
</script>

<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { useCustomLabelColors, type CustomColor } from '$lib/hooks/useCustomLabelColors';
    import { getColorByLabel } from '$lib/utils';
    import type { BoundingBox } from '$lib/types';
    import {
        acquireMaskRendererWorker,
        releaseMaskRendererWorker
    } from '$lib/workers/maskRendererPool';
    import {
        drawBoxesOnContext,
        transformBoxes,
        type RenderGeometry,
        type SourceCrop
    } from '$lib/workers/maskRendererUtils';

    interface InstanceAnnotation {
        annotation_type: 'segmentation_mask';
        annotation_label_name: string;
        segmentation_mask?: number[] | null;
        object_detection_details?: BoundingBox;
        color?: string;
        opacity?: number;
    }

    interface ObjectDetectionAnnotation {
        annotation_type: 'object_detection';
        annotation_label_name: string;
        object_detection_details: BoundingBox;
        segmentation_mask?: undefined;
        color?: string;
        opacity?: number;
    }

    type AnnotationCanvasAnnotation = InstanceAnnotation | ObjectDetectionAnnotation;

    interface Props {
        sampleId: string;
        sourceWidth: number;
        sourceHeight: number;
        outputWidth?: number;
        outputHeight?: number;
        objectFit?: 'contain' | 'cover';
        sourceCrop?: SourceCrop;
        annotations?: AnnotationCanvasAnnotation[];
        alpha?: number;
        className?: string;
    }

    const {
        sampleId,
        sourceWidth,
        sourceHeight,
        outputWidth,
        outputHeight,
        objectFit = 'contain',
        sourceCrop,
        annotations = [],
        alpha = 0.4,
        className = ''
    }: Props = $props();

    const canvasWidth = $derived(Math.max(1, Math.round(outputWidth ?? sourceWidth)));
    const canvasHeight = $derived(Math.max(1, Math.round(outputHeight ?? sourceHeight)));

    const { customLabelColorsStore } = useCustomLabelColors();

    let canvasEl: HTMLCanvasElement | null = null;
    let worker: Worker | null = null;
    let workerReady = false;
    let hasOffscreen = false;
    let hasMainThreadContext = false;
    // Shared workers multiplex multiple canvases
    const canvasId = `${sampleId}-${createCanvasInstanceSuffix()}`;

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

    interface ContextOptions {
        willReadFrequently?: boolean;
    }

    const getMainThreadContext = (options?: ContextOptions): CanvasRenderingContext2D | null => {
        if (!canvasEl || hasOffscreen) {
            return null;
        }

        const context = canvasEl.getContext('2d', options) as CanvasRenderingContext2D | null;
        if (context) {
            hasMainThreadContext = true;
        }
        return context;
    };

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

    const resolveAnnotationColor = (
        annotation: AnnotationCanvasAnnotation,
        colorAlpha: number,
        customLabelColors: CustomLabelColorMap
    ): [number, number, number, number] => {
        if (!annotation.color) {
            return resolveLabelColor(
                annotation.annotation_label_name || 'label',
                colorAlpha,
                customLabelColors
            );
        }

        const [r, g, b] = rgbaParser(annotation.color);
        return [r, g, b, Math.round(clampAlpha(annotation.opacity ?? colorAlpha) * 255)];
    };

    const toCloneableRLE = (mask?: ArrayLike<number> | null): number[] => {
        if (!mask?.length) {
            return [];
        }

        // Ensure worker postMessage receives a plain cloneable array (no reactive proxies).
        if (Array.isArray(mask)) {
            return mask.slice();
        }

        return Array.from(mask, (value) => Number(value) || 0);
    };

    // Collect mask RLEs and any available bounding boxes in image space.
    const buildRenderPayload = (
        customLabelColors: CustomLabelColorMap
    ): { masks: MaskPayload[]; boxes: BoxPayload[] } => {
        const masks: MaskPayload[] = [];
        const boxes: BoxPayload[] = [];

        for (const annotation of annotations) {
            const rle = toCloneableRLE(annotation.segmentation_mask);
            if (rle.length) {
                masks.push({
                    rle,
                    color: resolveAnnotationColor(annotation, alpha, customLabelColors)
                });
            }

            // We also include boxes for instance masks when bbox details are present.
            const bbox = annotation.object_detection_details;
            if (bbox) {
                boxes.push({
                    x: Math.round(bbox.x),
                    y: Math.round(bbox.y),
                    width: Math.round(bbox.width),
                    height: Math.round(bbox.height),
                    color: resolveAnnotationColor(annotation, 1, customLabelColors)
                });
            }
        }

        return { masks, boxes };
    };

    const render = (customLabelColors: CustomLabelColorMap = $customLabelColorsStore) => {
        const payload = buildRenderPayload(customLabelColors);
        const geometry: RenderGeometry = {
            sourceWidth,
            sourceHeight,
            outputWidth: canvasWidth,
            outputHeight: canvasHeight,
            objectFit,
            sourceCrop: sourceCrop ? { ...sourceCrop } : undefined
        };

        // The HTML canvas owns its backing size only until it is transferred. After transfer,
        // resizing it throws; subsequent OffscreenCanvas sizing happens in the worker.
        if (canvasEl && !hasOffscreen) {
            canvasEl.width = canvasWidth;
            canvasEl.height = canvasHeight;
        }

        if (!workerReady && payload.masks.length === 0) {
            if (!canvasEl) {
                return;
            }

            const ctx = getMainThreadContext({ willReadFrequently: true });
            if (!ctx) {
                return;
            }

            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            if (!payload.boxes.length) {
                return;
            }

            drawBoxesOnContext(ctx, transformBoxes(geometry, payload.boxes));
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
            const ctx = getMainThreadContext();
            ctx?.clearRect(0, 0, canvasWidth, canvasHeight);
        }

        worker.postMessage({
            type: 'render',
            canvasId,
            ...geometry,
            ...payload
        });
    };

    const handleWorkerMessage = (event: MessageEvent) => {
        // Ignore frames produced for other canvases that share the same worker instance.
        if (event.data?.type !== 'image' || event.data?.canvasId !== canvasId || !canvasEl) {
            return;
        }

        const {
            width: w,
            height: h,
            data,
            boxes = [],
            stroke = 2
        } = event.data as {
            canvasId: string;
            width: number;
            height: number;
            data: Uint8ClampedArray;
            boxes?: BoxPayload[];
            stroke?: number;
        };

        const ctx = getMainThreadContext({ willReadFrequently: true });
        if (!ctx) {
            return;
        }

        // Worker transfers pixel buffer ownership; clone into a fresh Uint8ClampedArray for ImageData.
        const imageData = new ImageData(new Uint8ClampedArray(data), w, h);
        ctx.putImageData(imageData, 0, 0);

        if (!boxes.length) {
            return;
        }

        drawBoxesOnContext(ctx, boxes, stroke);
    };

    const setupWorker = () => {
        if (!canvasEl || worker) {
            return;
        }

        worker = acquireMaskRendererWorker();
        worker.addEventListener('message', handleWorkerMessage);

        if (canvasEl.transferControlToOffscreen && !hasMainThreadContext) {
            try {
                // Preferred path: worker draws directly into the canvas through OffscreenCanvas.
                const offscreen = canvasEl.transferControlToOffscreen();
                worker.postMessage({ type: 'init', canvasId, canvas: offscreen }, [offscreen]);
                hasOffscreen = true;
            } catch {
                // A browser may reject transfer if any code acquired a context first. Keep the
                // canvas main-thread-owned and use worker-produced pixel buffers in that case.
                hasOffscreen = false;
            }
        }

        workerReady = true;
    };

    onMount(() => {
        rgbaParser = createColorParser();
    });

    onDestroy(() => {
        if (worker) {
            worker.postMessage({ type: 'dispose', canvasId });
            worker.removeEventListener('message', handleWorkerMessage);
            releaseMaskRendererWorker(worker);
            worker = null;
        }
    });

    $effect(() => {
        const customLabelColors = $customLabelColorsStore;
        render(customLabelColors);
    });
</script>

<canvas bind:this={canvasEl} class={className}></canvas>

<style>
    canvas {
        display: block;
    }
</style>
