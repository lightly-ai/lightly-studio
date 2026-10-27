<script lang="ts">
    import { T, useParentObject3D, useTask, useThrelte } from '@threlte/core';
    import { DoubleSide, Group, OrthographicCamera, Quaternion, Vector3 } from 'three';
    import type { Vector3 as CuboidSize } from '../../domain';
    import { getProjectedCuboidRadius } from './rotationRing';
    import { useRotationRing } from './useRotationRing.svelte';

    type RingCallbacks = Parameters<typeof useRotationRing>[0];
    interface Props extends RingCallbacks {
        size: CuboidSize;
    }
    let { size, onTransformEnd, onInteractionStart, onInteractionCancel }: Props = $props();
    const { camera, renderer } = useThrelte();
    const parent = useParentObject3D();
    const interaction = useRotationRing({
        onTransformEnd: (object, snapshot) => onTransformEnd?.(object, snapshot),
        onInteractionStart: () => onInteractionStart?.(),
        onInteractionCancel: () => onInteractionCancel?.()
    });
    const { hovered } = interaction;
    let ring = $state<Group>();
    let radius = $state(1);
    let unit = $state(0.01);
    const orientation = new Quaternion();
    const direction = new Vector3();

    useTask(
        () => {
            const object = parent.current;
            const view = camera.current;
            if (!object || !ring || !(view instanceof OrthographicCamera)) return;
            unit =
                (view.top - view.bottom) /
                (view.zoom * Math.max(renderer.domElement.clientHeight, 1));
            object.getWorldQuaternion(orientation);
            radius =
                getProjectedCuboidRadius(size, orientation, view.getWorldDirection(direction)) +
                24 * unit;
            ring.quaternion
                .copy(orientation)
                .invert()
                .multiply(view.getWorldQuaternion(new Quaternion()));
        },
        { autoInvalidate: false }
    );
</script>

<T.Group bind:ref={ring}>
    <T.Mesh
        renderOrder={1000}
        onpointerenter={() => interaction.setHovered(true)}
        onpointerleave={() => interaction.setHovered(false)}
        onpointerdown={interaction.onPointerDown}
    >
        <T.RingGeometry args={[radius - 8 * unit, radius + 8 * unit, 128]} />
        <T.MeshBasicMaterial transparent opacity={0} depthWrite={false} side={DoubleSide} />
    </T.Mesh>
    <T.Mesh renderOrder={1001} raycast={() => {}}>
        <T.RingGeometry args={[radius - unit, radius + unit, 128]} />
        <T.MeshBasicMaterial
            color={$hovered ? '#fbbf24' : '#e2e8f0'}
            transparent
            opacity={0.85}
            depthTest={false}
            depthWrite={false}
            side={DoubleSide}
        />
    </T.Mesh>
    <T.Mesh position={[0, radius, 0]} renderOrder={1002} raycast={() => {}}>
        <T.CircleGeometry args={[5 * unit, 24]} />
        <T.MeshBasicMaterial
            color="#fbbf24"
            depthTest={false}
            depthWrite={false}
            side={DoubleSide}
        />
    </T.Mesh>
</T.Group>
