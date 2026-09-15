<script lang="ts">
    import { T } from '@threlte/core';
    import { Vector3 } from 'three';
    import type { AnnotationClass, Bounds3, CuboidAnnotation } from '../domain';
    import { createCuboidWireframeGeometry } from './cuboidGeometry';

    /** Renders static annotation cuboids and their local +x heading indicators. */
    interface Props {
        /** Cuboids to render in the active point-cloud frame. */
        cuboids: readonly CuboidAnnotation[];
        /** Annotation classes used to resolve each cuboid's display color. */
        annotationClasses: readonly AnnotationClass[];
        /** Bounds of the point cloud containing the cuboids. */
        pointCloudBounds: Bounds3;
    }

    interface RenderCuboid {
        annotation: CuboidAnnotation;
        geometry: ReturnType<typeof createCuboidWireframeGeometry>;
        headingOrigin: Vector3;
        arrowLength: number;
    }

    let { cuboids, annotationClasses }: Props = $props();
    let renderCuboids = $state<RenderCuboid[]>([]);

    $effect(() => {
        const nextCuboids = cuboids.map((annotation) => ({
            annotation,
            geometry: createCuboidWireframeGeometry(annotation.size),
            headingOrigin: new Vector3(annotation.size[0] / 2, 0, 0),
            arrowLength: Math.max(annotation.size[0] * 0.35, 0.75)
        }));
        renderCuboids = nextCuboids;

        return () => nextCuboids.forEach(({ geometry }) => geometry.dispose());
    });

    function classColor(annotationClassId: string): string {
        return annotationClasses.find(({ id }) => id === annotationClassId)?.color ?? '#ffffff';
    }
</script>

{#each renderCuboids as item (item.annotation.id)}
    {@const color = classColor(item.annotation.annotationClassId)}
    <T.Group
        position={[...item.annotation.center]}
        quaternion={[...item.annotation.rotation]}
        userData={{ annotationId: item.annotation.id }}
    >
        <T.LineSegments geometry={item.geometry}>
            <T.LineBasicMaterial {color} />
        </T.LineSegments>
        <T.ArrowHelper
            args={[new Vector3(1, 0, 0), item.headingOrigin, item.arrowLength, color, 0.35, 0.2]}
        />
    </T.Group>
{/each}
