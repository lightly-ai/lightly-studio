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
</script>

<Canvas>
    <PointCloudScene
        batch={props.batch}
        cameraCuboid={props.cameraMode === 'perspective' ? undefined : selectedCuboid}
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
