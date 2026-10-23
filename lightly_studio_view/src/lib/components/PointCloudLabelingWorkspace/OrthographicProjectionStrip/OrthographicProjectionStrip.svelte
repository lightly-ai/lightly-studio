<script lang="ts">
    import SceneViewport from '../SceneViewport/SceneViewport.svelte';
    import type { ColorMode, PointBatch } from '$lib/components/PointCloudViewer';
    import type {
        AnnotationClass,
        AnnotationSource,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        CameraMode
    } from '../domain';

    interface Props {
        batch: PointBatch;
        colorMode: ColorMode;
        pointCloudBounds?: Bounds3;
        fitKey?: string;
        cuboids: readonly CuboidAnnotation[];
        annotationClasses: readonly AnnotationClass[];
        annotationSources: readonly AnnotationSource[];
        selectedAnnotationId?: string | null;
        hoveredAnnotationId?: string | null;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
    }

    let {
        batch,
        colorMode,
        pointCloudBounds,
        fitKey,
        cuboids,
        annotationClasses,
        annotationSources,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        onselect,
        onhover
    }: Props = $props();

    const views: readonly { mode: CameraMode; label: string }[] = [
        { mode: 'top', label: 'Top' },
        { mode: 'side', label: 'Side' },
        { mode: 'front', label: 'Front' }
    ];
</script>

<div class="grid h-full min-h-0 grid-cols-3 gap-1 border-t bg-background p-1">
    {#each views as view (view.mode)}
        <div
            class="relative min-h-0 overflow-hidden rounded border"
            data-testid={`projection-${view.mode}`}
        >
            <div
                class="pointer-events-none absolute left-2 top-1 z-10 rounded bg-background/80 px-1.5 py-0.5 text-xs text-muted-foreground"
            >
                {view.label}
            </div>
            <SceneViewport
                {batch}
                {colorMode}
                {pointCloudBounds}
                {fitKey}
                {cuboids}
                {annotationClasses}
                {annotationSources}
                {selectedAnnotationId}
                {hoveredAnnotationId}
                activeTool="select"
                cameraMode={view.mode}
                {onselect}
                {onhover}
            />
        </div>
    {/each}
</div>
