<script lang="ts">
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import CuboidLayer from '../../CuboidLayer/CuboidLayer.svelte';
    import OriginAxes from '../../OriginAxes/OriginAxes.svelte';
    import EgoRangeRing from '../../EgoRange/EgoRangeRing.svelte';
    import EgoDistanceLine from '../../EgoRange/EgoDistanceLine.svelte';
    import { showsEgoRangeOverlay } from '../../EgoRange/showsEgoRangeOverlay';
    import ReleaseWebGLContext from './ReleaseWebGLContext';
    import { useSceneViewportContext } from '../sceneViewportContext';
    import { getAnnotationPointClipping } from '../annotationPointClipping';
    const { getProps, interaction } = useSceneViewportContext();
    const props = $derived(getProps());
    const selectedCuboid = $derived(
        props.cuboids.find((annotation) => annotation.id === props.selectedAnnotationId)
    );
    const clippingPlanes = $derived(getAnnotationPointClipping(props.cameraMode, selectedCuboid));
    const rangeHighlight = $derived(
        props.egoRange
            ? {
                  center: [props.egoRange.position[0], props.egoRange.position[1]] as const,
                  radius: props.egoRange.radius
              }
            : undefined
    );
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
    <ReleaseWebGLContext />
    <PointCloudScene
        batch={props.batch}
        cameraCuboid={props.cameraMode === 'perspective' ? undefined : selectedCuboid}
        {clippingPlanes}
        highlightCuboid={draftHighlight ?? selectedCuboid}
        {rangeHighlight}
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
    {#if props.egoRange && showsEgoRangeOverlay(props.cameraMode)}
        <EgoRangeRing range={props.egoRange} />
        {#if selectedCuboid}
            <EgoDistanceLine egoPosition={props.egoRange.position} target={selectedCuboid.center} />
        {/if}
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
        isEditingMode={props.isEditingMode}
        onselect={props.onselect}
        onhover={props.onhover}
        onCreateCuboid={props.onCreateCuboid}
        onCuboidDraftChange={props.onCuboidDraftChange}
        onCuboidTransform={props.onCuboidTransform}
    />
</Canvas>
