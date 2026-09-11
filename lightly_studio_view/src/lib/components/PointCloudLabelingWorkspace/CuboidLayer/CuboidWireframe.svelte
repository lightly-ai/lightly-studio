<script lang="ts">
    import { T } from '@threlte/core';
    import { BufferGeometry, Vector3 } from 'three';
    import type { Color } from 'three';
    import { createCuboidWireframeGeometry } from './cuboidGeometry';
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

    /**
     * Renders a cuboid wireframe (12 edges) and heading arrow in local space.
     * Geometry is recreated reactively whenever the cuboid size changes.
     */
    interface Props {
        /** Cuboid annotation providing size, center and rotation. */
        annotation: CuboidAnnotation;
        /** Edge and arrow color. */
        edgeColor: Color;
        /** Arrow head and shaft color (unmodified class color). */
        baseColor: string;
    }

    let { annotation, edgeColor, baseColor }: Props = $props();

    let wireframeGeometry = $state<ReturnType<typeof createCuboidWireframeGeometry>>(
        new BufferGeometry()
    );

    $effect(() => {
        const geo = createCuboidWireframeGeometry(annotation.size);
        wireframeGeometry = geo;
        return () => geo.dispose();
    });
</script>

<T.Group position={[...annotation.center]} quaternion={[...annotation.rotation]}>
    <T.LineSegments geometry={wireframeGeometry}>
        <T.LineBasicMaterial color={edgeColor} />
    </T.LineSegments>
    <T.ArrowHelper
        args={[
            new Vector3(1, 0, 0),
            new Vector3(annotation.size[0] / 2, 0, 0),
            Math.max(annotation.size[0] * 0.35, 0.75),
            baseColor,
            0.35,
            0.2
        ]}
    />
</T.Group>
