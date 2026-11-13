<script lang="ts">
    import { T, useParentObject3D, useTask, useThrelte } from '@threlte/core';
    import { DoubleSide, Group, OrthographicCamera, Quaternion } from 'three';
    import { useMoveHandle } from './useMoveHandle.svelte';

    let {
        onTransformEnd,
        onTransformPreview,
        onInteractionStart,
        onInteractionCancel
    }: Parameters<typeof useMoveHandle>[0] = $props();
    const { camera, renderer } = useThrelte();
    const parent = useParentObject3D();
    const interaction = useMoveHandle({
        onTransformEnd: (object, snapshot) => onTransformEnd?.(object, snapshot),
        onTransformPreview: (object) => onTransformPreview?.(object),
        onInteractionStart: () => onInteractionStart?.(),
        onInteractionCancel: () => onInteractionCancel?.()
    });
    const { hovered } = interaction;
    let handle = $state<Group>();
    let unit = $state(0.01);

    useTask(
        () => {
            const object = parent.current;
            const view = camera.current;
            if (!object || !handle || !(view instanceof OrthographicCamera)) return;
            unit =
                (view.top - view.bottom) /
                (view.zoom * Math.max(renderer.domElement.clientHeight, 1));
            // Face the camera regardless of the cuboid's rotation.
            handle.quaternion
                .copy(object.getWorldQuaternion(new Quaternion()))
                .invert()
                .multiply(view.getWorldQuaternion(new Quaternion()));
        },
        { autoInvalidate: false }
    );
</script>

<T.Group bind:ref={handle}>
    <T.Mesh
        renderOrder={1000}
        onpointerenter={() => interaction.setHovered(true)}
        onpointerleave={() => interaction.setHovered(false)}
        onpointerdown={interaction.onPointerDown}
    >
        <T.CircleGeometry args={[14 * unit, 32]} />
        <T.MeshBasicMaterial transparent opacity={0} depthWrite={false} side={DoubleSide} />
    </T.Mesh>
    <T.Mesh renderOrder={1002} raycast={() => {}}>
        <T.CircleGeometry args={[($hovered ? 10 : 8) * unit, 32]} />
        <T.MeshBasicMaterial
            color="#ffffff"
            depthTest={false}
            depthWrite={false}
            side={DoubleSide}
        />
    </T.Mesh>
    <T.Mesh renderOrder={1003} raycast={() => {}}>
        <T.CircleGeometry args={[($hovered ? 8 : 6) * unit, 32]} />
        <T.MeshBasicMaterial
            color="#fbbf24"
            depthTest={false}
            depthWrite={false}
            side={DoubleSide}
        />
    </T.Mesh>
</T.Group>
