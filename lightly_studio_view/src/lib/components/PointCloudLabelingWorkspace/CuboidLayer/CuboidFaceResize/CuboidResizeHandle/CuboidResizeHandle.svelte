<script lang="ts">
    import { T, useParentObject3D, useThrelte, useTask } from '@threlte/core';
    import type { IntersectionEvent } from '@threlte/extras';
    import { Color, Group, PerspectiveCamera, Vector3 } from 'three';

    const AXIS_COLORS = ['#e83030', '#30e830', '#3030e8'] as const;
    /** Overall size factor — same meaning as TransformControls `size`. */
    const HANDLE_SIZE = 0.5;
    const SHAFT_LENGTH = 0.5;
    const SHAFT_RADIUS = 0.02;
    const CAP_SIZE = 0.08;
    /**
     * Maps handle-local X and Y axes to the parent-space scale component that stretches them.
     * Derived from the euler rotations in FACE_DEFINITIONS:
     *   axisIndex 0 [0, π/2, 0]:  localX→parentZ(2), localY→parentY(1)
     *   axisIndex 1 [-π/2, 0, 0]: localX→parentX(0), localY→parentZ(2)
     *   axisIndex 2 [0, 0, 0]:    localX→parentX(0), localY→parentY(1)
     */
    const PERP_SCALE_INDICES = [
        [2, 1],
        [0, 2],
        [0, 1]
    ];

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
            // Cap mirrors TransformControls: prevents handles growing unbounded at extreme distances.
            const eyeDistance = Math.min(cameraDistance * Math.tan((Math.PI / 180) * (fov / 2)), 7);
            const base = eyeDistance * HANDLE_SIZE;
            // The annotation group's scale is modified during a resize drag (scale[axis] = newSize/origSize).
            // Each local axis is compensated individually so the cap and shaft cross-section stay constant
            // in screen space even when the parent is scaled on the perpendicular axes.
            const parentScale = parentObject.scale;
            const [xIdx, yIdx] = PERP_SCALE_INDICES[axisIndex];
            const sz =
                base /
                (parentScale.getComponent(axisIndex) > 0 ? parentScale.getComponent(axisIndex) : 1);
            const sx =
                base / (parentScale.getComponent(xIdx) > 0 ? parentScale.getComponent(xIdx) : 1);
            const sy =
                base / (parentScale.getComponent(yIdx) > 0 ? parentScale.getComponent(yIdx) : 1);
            scale = [sx, sy, sz];
        },
        { autoInvalidate: false }
    );
</script>

<!--
    Group is positioned at the face center with face euler applied so that
    local +Z points outward from the face. Shaft and cap are sized in local
    units and scaled to a constant screen-space size each frame.
-->
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
