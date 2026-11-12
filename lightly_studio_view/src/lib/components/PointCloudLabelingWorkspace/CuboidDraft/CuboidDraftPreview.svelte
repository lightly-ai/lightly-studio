<script lang="ts">
    import { T } from '@threlte/core';
    import { BoxGeometry, EdgesGeometry } from 'three';
    import type { CuboidBox } from './cuboidDraft';

    /** Translucent preview of the cuboid being drawn. */
    interface Props {
        /** Box to preview, in world space. */
        box: CuboidBox;
    }

    let { box }: Props = $props();
    const geometry = $derived(new BoxGeometry(...box.size));
    const edges = $derived(new EdgesGeometry(geometry));

    $effect(() => {
        return () => {
            geometry.dispose();
            edges.dispose();
        };
    });
</script>

<T.Mesh position={[...box.center]} {geometry}>
    <T.MeshBasicMaterial color="white" transparent opacity={0.2} depthWrite={false} />
</T.Mesh>
<T.LineSegments position={[...box.center]} geometry={edges}>
    <T.LineBasicMaterial color="white" />
</T.LineSegments>
