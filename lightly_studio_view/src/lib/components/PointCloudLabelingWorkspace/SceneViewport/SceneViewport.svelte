<script lang="ts">
    import { cn } from '$lib/utils';
    import { resolveSceneViewportProps } from './resolveSceneViewportProps';
    import type { Snippet } from 'svelte';
    import type { ColorMode, PointBatch, SceneViewState } from '$lib/components/PointCloudViewer';
    import type {
        AnnotationClass,
        AnnotationSource,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        Vector3,
        CameraMode,
        WorkspaceTool
    } from '../domain';
    import type { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';
    interface Props {
        header?: Snippet;
        tools?: Snippet;
        batch?: PointBatch;
        colorMode?: ColorMode;
        pointSize?: number;
        intensityRange?: [number, number];
        cuboids?: readonly CuboidAnnotation[];
        annotationClasses?: readonly AnnotationClass[];
        annotationSources?: readonly AnnotationSource[];
        transforms: ReturnType<typeof createCuboidTransformState>;
        pointCloudBounds?: Bounds3;
        fitKey?: string;
        selectedAnnotationId?: string | null;
        hoveredAnnotationId?: string | null;
        activeTool?: WorkspaceTool;
        cameraMode?: CameraMode;
        isScaleSource?: boolean;
        showNavigationHelpers?: boolean;
        showAnnotationTooltips?: boolean;
        showActiveBorder?: boolean;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
        onCreateCuboid?: (position: Vector3) => void;
        onCuboidTransform?: Parameters<typeof resolveSceneViewportProps>[0]['onCuboidTransform'];
        onPreviousTick?: () => void;
        onNextTick?: () => void;
        viewState?: SceneViewState | null;
        onViewStateChange?: (viewState: SceneViewState) => void;
    }
    import { useSceneViewport } from './useSceneViewport/useSceneViewport.svelte';
    import { provideSceneViewportContext } from './sceneViewportContext';
    import SceneViewportCanvas from './SceneViewportCanvas/SceneViewportCanvas.svelte';
    import SceneViewportOverlay from './SceneViewportOverlay/SceneViewportOverlay.svelte';
    // This wrapper forwards scene inputs and is not exposed as a custom element.
    // svelte-ignore custom_element_props_identifier
    let { pointSize = $bindable(2), ...inputs }: Props = $props();
    const viewportProps = $derived(resolveSceneViewportProps({ ...inputs, pointSize }));
    const interaction = useSceneViewport(() => viewportProps);
    provideSceneViewportContext({ getProps: () => viewportProps, interaction });
</script>

<!-- Viewports receive focus for keyboard navigation. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
    class={cn(
        'relative h-full w-full',
        viewportProps.activeTool === 'create-cuboid' && 'cursor-crosshair'
    )}
    role="application"
    aria-label="Point-cloud scene viewport"
    aria-current={interaction.isActive ? 'true' : undefined}
    data-testid="workspace-scene-viewport"
    tabindex="0"
    onpointerenter={interaction.activate}
    onpointerdown={interaction.activate}
    onfocusin={interaction.activate}
    onmousemove={interaction.handleMouseMove}
    bind:this={interaction.viewport}
>
    <SceneViewportCanvas />
    <SceneViewportOverlay />
</div>
