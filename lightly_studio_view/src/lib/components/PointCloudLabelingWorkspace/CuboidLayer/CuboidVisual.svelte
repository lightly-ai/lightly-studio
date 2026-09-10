<script lang="ts">
    import { T } from '@threlte/core';
    import { Color, Vector3 } from 'three';
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

    function onClick(): void {
        const selected = selectCuboid({
            annotationId: item.annotation.id,
            activeTool,
            onselect
        });
        if (selected) onselected?.();
    }
</script>

<T.LineSegments geometry={item.geometry}>
    <T.LineBasicMaterial color={edgeColor} />
</T.LineSegments>
<T.ArrowHelper
    args={[new Vector3(1, 0, 0), item.headingOrigin, item.arrowLength, baseColor, 0.35, 0.2]}
/>
<T.Mesh
    visible={false}
    onclick={onClick}
    onpointerenter={() => onhover?.(item.annotation.id, null)}
    onpointerleave={() => onhover?.(null, null)}
>
    <T.BoxGeometry args={[...item.annotation.size]} />
    <T.MeshBasicMaterial />
</T.Mesh>
