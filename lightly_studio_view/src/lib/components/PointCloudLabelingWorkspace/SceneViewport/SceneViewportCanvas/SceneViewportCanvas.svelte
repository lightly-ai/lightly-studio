<script lang="ts">
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import CuboidLayer from '../../CuboidLayer/CuboidLayer.svelte';
    import { GroundPlane } from '../../GroundPlane';
    import OriginAxes from '../../OriginAxes/OriginAxes.svelte';
    import { useSceneViewportContext } from '../sceneViewportContext';
    import { getAnnotationPointClipping } from '../annotationPointClipping';
    const { getProps, interaction } = useSceneViewportContext();
    const props = $derived(getProps());
    const clippingPlanes = $derived(
        getAnnotationPointClipping(
            props.cameraMode,
            props.cuboids.find((annotation) => annotation.id === props.selectedAnnotationId)
        )
    );
</script>

<Canvas>
    <PointCloudScene
        batch={props.batch}
        {clippingPlanes}
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
    <GroundPlane pointCloudBounds={interaction.groundPlaneBounds} />
    <OriginAxes />
    <CuboidLayer
        cameraMode={props.cameraMode}
        cuboids={props.cuboids}
        annotationClasses={props.annotationClasses}
        transforms={props.transforms}
        groundPlaneBounds={interaction.groundPlaneBounds}
        selectedAnnotationId={props.selectedAnnotationId}
        hoveredAnnotationId={props.hoveredAnnotationId}
        activeTool={props.activeTool}
        onselect={props.onselect}
        onhover={props.onhover}
        onCreateCuboid={props.onCreateCuboid}
        onCuboidTransform={props.onCuboidTransform}
    />
</Canvas>
