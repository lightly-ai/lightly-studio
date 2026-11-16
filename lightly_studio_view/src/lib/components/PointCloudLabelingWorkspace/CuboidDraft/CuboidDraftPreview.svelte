<script lang="ts">
    import { T } from '@threlte/core';
    import { onDestroy } from 'svelte';
    import { BoxGeometry, EdgesGeometry } from 'three';
    import type { CuboidBox } from './cuboidDraft';

    /** Translucent preview of the cuboid being drawn. */
    interface Props {
        /** Box to preview, in world space. */
        box: CuboidBox;
    }

    let { box }: Props = $props();
    // One unit box scaled to the draft, so pointer moves do not allocate geometries.
    const geometry = new BoxGeometry(1, 1, 1);
    const edges = new EdgesGeometry(geometry);

    onDestroy(() => {
        geometry.dispose();
        edges.dispose();
    });
</script>

<!-- Draw on top so the preview stays visible through dense point-cloud regions. -->
<T.Mesh
    position={[...box.center]}
    rotation={[0, 0, box.yaw]}
    scale={[...box.size]}
    {geometry}
    renderOrder={999}
>
    <T.MeshBasicMaterial
        color="white"
        transparent
        opacity={0.2}
        depthWrite={false}
        depthTest={false}
    />
</T.Mesh>
<T.LineSegments
    position={[...box.center]}
    rotation={[0, 0, box.yaw]}
    scale={[...box.size]}
    geometry={edges}
    renderOrder={1000}
>
    <T.LineBasicMaterial color="white" depthTest={false} />
</T.LineSegments>
