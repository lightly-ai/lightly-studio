<script lang="ts">
    import { T, useParentObject3D, useThrelte, useTask } from '@threlte/core';
    import type { IntersectionEvent } from '@threlte/extras';
    import { Color, Group, OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';

    import { computeHandleScale } from './cuboidResizeHandle';

    const AXIS_COLORS = ['#e83030', '#30e830', '#3030e8'] as const;
    const SHAFT_LENGTH = 0.5;
    const SHAFT_RADIUS = 0.02;
    const CAP_SIZE = 0.08;

    interface Props {
        position: [number, number, number];
        euler: readonly [number, number, number];
        axisIndex: 0 | 1 | 2;
        isActive: boolean;
        onpointerenter?: () => void;
        onpointerleave?: () => void;
        onpointerdown?: (event: IntersectionEvent<PointerEvent>) => void;
    }

    let {
        position,
        euler,
        axisIndex,
        isActive,
        onpointerenter,
        onpointerleave,
        onpointerdown
    }: Props = $props();

    const color = $derived.by(() => {
        const baseHex = AXIS_COLORS[axisIndex];
        const activeHex = '#' + new Color(baseHex).lerp(new Color(1, 1, 1), 0.5).getHexString();
        return new Color(isActive ? activeHex : baseHex);
    });

    const { camera } = useThrelte();
    const parent = useParentObject3D();
    const worldPosition = new Vector3();

    let groupRef: Group | undefined = $state();
    let scale = $state<[number, number, number]>([1, 1, 1]);

    useTask(
        () => {
            const parentObject = parent.current;
            if (!parentObject || !groupRef) return;
            groupRef.getWorldPosition(worldPosition);
            const currentCamera = camera.current;
            const cameraDistance = currentCamera.position.distanceTo(worldPosition);
            const fov = currentCamera instanceof PerspectiveCamera ? currentCamera.fov : 60;
            const parentScale = parentObject.scale;
            scale = computeHandleScale({
                cameraDistance,
                fov,
                orthographicSpan:
                    currentCamera instanceof OrthographicCamera
                        ? (currentCamera.top - currentCamera.bottom) / currentCamera.zoom
                        : undefined,
                parentScale: [parentScale.x, parentScale.y, parentScale.z],
                axisIndex
            });
        },
        { autoInvalidate: false }
    );
</script>

<!-- Face-local +Z points outward; scale keeps the handle size stable on screen. -->
<T.Group bind:ref={groupRef} {position} rotation={[...euler]} {scale}>
    <!-- Shaft: CylinderGeometry is along Y by default; rotate -90° on X → along +Z -->
    <T.Mesh
        position={[0, 0, SHAFT_LENGTH / 2]}
        rotation={[-Math.PI / 2, 0, 0]}
        renderOrder={999}
        {onpointerenter}
        {onpointerleave}
        {onpointerdown}
    >
        <T.CylinderGeometry args={[SHAFT_RADIUS, SHAFT_RADIUS, SHAFT_LENGTH, 8]} />
        <T.MeshBasicMaterial {color} depthTest={false} />
    </T.Mesh>

    <!-- Cap: box at the tip of the shaft -->
    <T.Mesh
        position={[0, 0, SHAFT_LENGTH + CAP_SIZE / 2]}
        renderOrder={999}
        {onpointerenter}
        {onpointerleave}
        {onpointerdown}
    >
        <T.BoxGeometry args={[CAP_SIZE, CAP_SIZE, CAP_SIZE]} />
        <T.MeshBasicMaterial {color} depthTest={false} />
    </T.Mesh>
</T.Group>
