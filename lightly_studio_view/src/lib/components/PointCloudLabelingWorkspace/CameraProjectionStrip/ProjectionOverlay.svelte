<script lang="ts">
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';
    import {
        projectAnnotations,
        projectPointCloudData,
        type ProjectedPointData
    } from './projectionOverlay';
    import {
        DEFAULT_PROJECTION_SETTINGS,
        type ProjectionColorMode,
        type ProjectionSettings
    } from './projectionSettings';

    interface Props {
        batch?: PointBatch;
        annotations: readonly AnnotationView[];
        projection?: CameraProjectionView;
        settings?: ProjectionSettings;
    }

    let {
        batch,
        annotations,
        projection,
        settings = DEFAULT_PROJECTION_SETTINGS
    }: Props = $props();
    let canvas: HTMLCanvasElement | undefined = $state();

    $effect(() => {
        if (!canvas || !projection) return;
        canvas.width = projection.width;
        canvas.height = projection.height;
        const context = canvas.getContext('2d');
        if (!context) return;
        context.clearRect(0, 0, projection.width, projection.height);
        if (batch && settings.showPoints) {
            const size = settings.pointSize;
            const halfSize = size / 2;
            context.globalAlpha = settings.pointOpacity;
            const points = projectPointCloudData(batch, projection);
            const metrics = getColorMetrics(settings.colorMode);
            const ranges = metrics.map((metric) => {
                const values = points.map((point) => getMetricValue(point, metric));
                return [Math.min(...values), Math.max(...values)] as const;
            });
            for (const [index, point] of points.entries()) {
                context.fillStyle = 'rgba(0, 0, 0, 0.8)';
                context.fillRect(
                    point.x - halfSize - 1,
                    point.y - halfSize - 1,
                    size + 2,
                    size + 2
                );
                context.fillStyle = getPointColor(
                    point,
                    settings,
                    normalizePoint(point, metrics, ranges)
                );
                context.fillRect(point.x - halfSize, point.y - halfSize, size, size);
            }
        }
        if (settings.showAnnotations) {
            context.globalAlpha = 1;
            context.strokeStyle = '#ff5c5c';
            context.lineWidth = 2;
            context.beginPath();
            for (const segment of projectAnnotations(annotations, projection)) {
                context.moveTo(segment.start.x, segment.start.y);
                context.lineTo(segment.end.x, segment.end.y);
            }
            context.stroke();
        }
    });

    type ColorMetric = 'depth' | 'height' | 'intensity' | 'distance' | 'density';

    function getColorMetrics(mode: ProjectionColorMode): ColorMetric[] {
        if (mode === 'height-distance') return ['height', 'distance'];
        if (mode === 'height-density') return ['height', 'density'];
        if (mode === 'height') return ['height'];
        if (mode === 'intensity') return ['intensity'];
        if (mode === 'distance') return ['distance'];
        if (mode === 'density') return ['density'];
        return ['depth'];
    }

    function getMetricValue(point: ProjectedPointData, metric: ColorMetric): number {
        return point[metric];
    }

    function normalizePoint(
        point: ProjectedPointData,
        metrics: ColorMetric[],
        ranges: readonly (readonly [number, number])[]
    ): number {
        return (
            metrics.reduce(
                (sum, metric, index) =>
                    sum + normalize(getMetricValue(point, metric), ...ranges[index]),
                0
            ) / metrics.length
        );
    }

    function normalize(value: number, min: number, max: number): number {
        return max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)));
    }

    function getPointColor(
        point: ProjectedPointData,
        settings: ProjectionSettings,
        normalizedValue: number
    ): string {
        const hue = 230 - normalizedValue * 230;
        return `hsl(${hue} 90% 55%)`;
    }
</script>

{#if projection}
    <canvas
        bind:this={canvas}
        class="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
    ></canvas>
{/if}
