<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { Color, Vector3 } from 'three';
    import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';
    import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
    import type {
        CuboidHandle,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { createCuboidRenderItems } from './cuboidRenderItems';
    import { selectCuboid } from './cuboidSelection';

    interface Props {
        /** Render resources and annotation metadata for this cuboid. */
        item: ReturnType<typeof createCuboidRenderItems>[number];
        /** Unmodified class color for the heading indicator. */
        baseColor: string;
        /** Interaction-aware edge color. */
        edgeColor: Color;
        /** Tool that determines whether clicking can select the cuboid. */
        activeTool: WorkspaceTool;
        /** Fires when the user selects or deselects a cuboid. */
        onselect?: (annotationId: string | null) => void;
        /** Fires when the pointer enters or leaves a cuboid. */
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
        /** Records that this click selected a cuboid instead of empty space. */
        onselected?: () => void;
    }

    let { item, baseColor, edgeColor, activeTool, onselect, onhover, onselected }: Props = $props();

    const { size } = useThrelte();
    const resolution = $derived([$size.width, $size.height] as [number, number]);

    function stopAnd(fn: () => void) {
        return (event: { stopPropagation(): void }) => {
            event.stopPropagation();
            fn();
        };
    }

    function onClick(): void {
        const selected = selectCuboid({
            annotationId: item.annotation.id,
            activeTool,
            onselect
        });
        if (selected) onselected?.();
    }
</script>

<T is={LineSegments2} geometry={item.geometry}>
    <T is={LineMaterial} color={edgeColor} linewidth={2} {resolution} />
</T>
<T.ArrowHelper
    args={[new Vector3(1, 0, 0), item.headingOrigin, item.arrowLength, baseColor, 0.35, 0.2]}
/>
<T.Mesh
    visible={false}
    onclick={stopAnd(onClick)}
    onpointerenter={stopAnd(() => onhover?.(item.annotation.id, null))}
    onpointerleave={stopAnd(() => onhover?.(null, null))}
>
    <T.BoxGeometry args={[...item.annotation.size]} />
    <T.MeshBasicMaterial />
</T.Mesh>
