<script lang="ts">
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import CuboidLayer from '../../CuboidLayer/CuboidLayer.svelte';
    import OriginAxes from '../../OriginAxes/OriginAxes.svelte';
    import { useSceneViewportContext } from '../sceneViewportContext';
    import { getAnnotationPointClipping } from '../annotationPointClipping';
    const { getProps, interaction } = useSceneViewportContext();
    const props = $derived(getProps());
    const selectedCuboid = $derived(
        props.cuboids.find((annotation) => annotation.id === props.selectedAnnotationId)
    );
    const clippingPlanes = $derived(getAnnotationPointClipping(props.cameraMode, selectedCuboid));
    // While a cuboid is drawn, the points that it takes in are highlighted in every viewport.
    const draftHighlight = $derived(
        props.draftCuboid
            ? {
                  center: props.draftCuboid.center,
                  size: props.draftCuboid.size,
                  rotation: [
                      0,
                      0,
                      Math.sin(props.draftCuboid.yaw / 2),
                      Math.cos(props.draftCuboid.yaw / 2)
                  ] as const,
                  keepOutside: true
              }
            : undefined
    );
</script>

<Canvas>
    <PointCloudScene
        batch={props.batch}
        cameraCuboid={props.cameraMode === 'perspective' ? undefined : selectedCuboid}
        {clippingPlanes}
        highlightCuboid={draftHighlight ?? selectedCuboid}
        colorMode={props.colorMode}
        pointSize={props.pointSize}
        intensityRange={props.intensityRange}
        fitKey={props.fitKey}
        activeTool={props.activeTool}
        cameraMode={props.cameraMode}
        isScaleSource={props.isScaleSource}
        isActive={() => interaction.isActive}
        navigationId={interaction.navigationId}
        viewState={props.viewState}
        onViewStateChange={props.onViewStateChange}
    />
    {#if props.cameraMode === 'perspective'}
        <OriginAxes />
    {/if}
    <CuboidLayer
        cameraMode={props.cameraMode}
        cuboids={props.cuboids}
        annotationClasses={props.annotationClasses}
        transforms={props.transforms}
        groundPlaneBounds={interaction.groundPlaneBounds}
        pointBatch={props.batch}
        tick={props.tick}
        selectedAnnotationId={props.selectedAnnotationId}
        hoveredAnnotationId={props.hoveredAnnotationId}
        activeTool={props.activeTool}
        onselect={props.onselect}
        onhover={props.onhover}
        onCreateCuboid={props.onCreateCuboid}
        onCuboidDraftChange={props.onCuboidDraftChange}
        onCuboidTransform={props.onCuboidTransform}
    />
</Canvas>
