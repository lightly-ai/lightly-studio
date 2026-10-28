<script lang="ts">
    import { T, useParentObject3D, useThrelte, useTask } from '@threlte/core';
    import type { IntersectionEvent } from '@threlte/extras';
    import { Color, Group, OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';

    import { computeHandleScale } from './cuboidResizeHandle';

    const AXIS_COLORS = ['#e83030', '#30e830', '#3030e8'] as const;
    // Perspective handles keep their original proportions. Orthographic handles are larger, and
    // both get invisible hit areas bigger than the visuals so they are easy to grab.
    const PERSPECTIVE_DIMENSIONS = {
        shaftLength: 0.5,
        shaftRadius: 0.02,
        capSize: 0.08,
        hitShaftRadius: 0.06,
        hitCapSize: 0.2
    };
    const ORTHOGRAPHIC_DIMENSIONS = {
        shaftLength: 1,
        shaftRadius: 0.05,
        capSize: 0.24,
        hitShaftRadius: 0.24,
        hitCapSize: 0.72,
        tileWidth: 0.25,
        tileThickness: 0.25,
        hitTileWidth: 0.5,
        hitTileThickness: 0.5
    };

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
    let isOrthographic = $state(false);
    const dims = $derived(isOrthographic ? ORTHOGRAPHIC_DIMENSIONS : PERSPECTIVE_DIMENSIONS);
    let scale = $state<[number, number, number]>([1, 1, 1]);

    useTask(
        () => {
            const parentObject = parent.current;
            if (!parentObject || !groupRef) return;
            groupRef.getWorldPosition(worldPosition);
            const currentCamera = camera.current;
            isOrthographic = currentCamera instanceof OrthographicCamera;
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
    {#if isOrthographic}
        <!-- Orthographic: a flat rectangle on the face edge; the in-plane depth axis is hidden. -->
        <T.Mesh
            position={[0, 0, ORTHOGRAPHIC_DIMENSIONS.tileThickness / 2]}
            scale={isActive ? 1.25 : 1}
            renderOrder={999}
            raycast={() => {}}
        >
            <T.BoxGeometry
                args={[
                    ORTHOGRAPHIC_DIMENSIONS.tileWidth,
                    ORTHOGRAPHIC_DIMENSIONS.tileWidth,
                    ORTHOGRAPHIC_DIMENSIONS.tileThickness
                ]}
            />
            <T.MeshBasicMaterial {color} depthTest={false} />
        </T.Mesh>
        <T.Mesh
            position={[0, 0, ORTHOGRAPHIC_DIMENSIONS.tileThickness / 2]}
            renderOrder={1000}
            {onpointerenter}
            {onpointerleave}
            {onpointerdown}
        >
            <T.BoxGeometry
                args={[
                    ORTHOGRAPHIC_DIMENSIONS.hitTileWidth,
                    ORTHOGRAPHIC_DIMENSIONS.hitTileWidth,
                    ORTHOGRAPHIC_DIMENSIONS.hitTileThickness
                ]}
            />
            <T.MeshBasicMaterial transparent opacity={0} depthTest={false} depthWrite={false} />
        </T.Mesh>
    {:else}
        <!-- Shaft: CylinderGeometry is along Y by default; rotate -90° on X → along +Z -->
        <T.Mesh
            position={[0, 0, dims.shaftLength / 2]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={999}
            raycast={() => {}}
        >
            <T.CylinderGeometry args={[dims.shaftRadius, dims.shaftRadius, dims.shaftLength, 8]} />
            <T.MeshBasicMaterial {color} depthTest={false} />
        </T.Mesh>

        <!-- Cap: box at the tip of the shaft -->
        <T.Mesh
            position={[0, 0, dims.shaftLength + dims.capSize / 2]}
            scale={isActive ? 1.25 : 1}
            renderOrder={999}
            raycast={() => {}}
        >
            <T.BoxGeometry args={[dims.capSize, dims.capSize, dims.capSize]} />
            <T.MeshBasicMaterial {color} depthTest={false} />
        </T.Mesh>

        <!-- Hit areas: invisible and larger than the visuals; they own all pointer events -->
        <T.Mesh
            position={[0, 0, dims.shaftLength / 2]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={1000}
            {onpointerenter}
            {onpointerleave}
            {onpointerdown}
        >
            <T.CylinderGeometry
                args={[dims.hitShaftRadius, dims.hitShaftRadius, dims.shaftLength, 8]}
            />
            <T.MeshBasicMaterial transparent opacity={0} depthTest={false} depthWrite={false} />
        </T.Mesh>
        <T.Mesh
            position={[0, 0, dims.shaftLength + dims.capSize / 2]}
            renderOrder={1000}
            {onpointerenter}
            {onpointerleave}
            {onpointerdown}
        >
            <T.BoxGeometry args={[dims.hitCapSize, dims.hitCapSize, dims.hitCapSize]} />
            <T.MeshBasicMaterial transparent opacity={0} depthTest={false} depthWrite={false} />
        </T.Mesh>
    {/if}
</T.Group>
