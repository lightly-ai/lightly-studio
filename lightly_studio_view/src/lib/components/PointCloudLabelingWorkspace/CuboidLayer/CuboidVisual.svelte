<script lang="ts">
    import { T } from '@threlte/core';
    import { Color, DoubleSide, Vector3 } from 'three';
    import { createCuboidRenderItems } from './cuboidRenderItems';

    interface Props {
        /** Render resources and annotation metadata for this cuboid. */
        item: ReturnType<typeof createCuboidRenderItems>[number];
        /** Unmodified class color for the heading indicator and fill. */
        baseColor: string;
        /** Interaction-aware edge color. */
        edgeColor: Color;
        /** Whether this cuboid is currently hovered. */
        isHovered?: boolean;
        /** Whether this cuboid is currently selected. */
        isSelected?: boolean;
        /**
         * Fires when the pointer clicks this cuboid. All overlapping cuboids fire without
         * stopping propagation so the layer can pick the smallest-volume winner.
         */
        onhit?: (annotationId: string, volume: number) => void;
        /**
         * Fires when the pointer enters this cuboid. All overlapping cuboids fire without
         * stopping propagation so the layer can track the smallest-volume winner.
         */
        onhoverenter?: (annotationId: string, volume: number) => void;
        /** Fires when the pointer leaves this cuboid. */
        onhoverleave?: (annotationId: string) => void;
    }

    let {
        item,
        baseColor,
        edgeColor,
        isHovered = false,
        isSelected = false,
        onhit,
        onhoverenter,
        onhoverleave
    }: Props = $props();

    const volume = $derived(
        item.annotation.size[0] * item.annotation.size[1] * item.annotation.size[2]
    );
    const showFill = $derived(isHovered || isSelected);

    function onClick(): void {
        onhit?.(item.annotation.id, volume);
        // No stopPropagation — all overlapping cuboids fire so the layer picks the smallest.
    }
</script>

<T.LineSegments geometry={item.geometry}>
    <T.LineBasicMaterial color={edgeColor} />
</T.LineSegments>
<T.ArrowHelper
    args={[new Vector3(1, 0, 0), item.headingOrigin, item.arrowLength, baseColor, 0.35, 0.2]}
/>
{#if showFill}
    <T.Mesh>
        <T.BoxGeometry args={[...item.annotation.size]} />
        <T.MeshBasicMaterial
            color={baseColor}
            opacity={0.25}
            transparent={true}
            depthWrite={false}
            side={DoubleSide}
        />
    </T.Mesh>
{/if}
<T.Mesh
    visible={false}
    onclick={onClick}
    onpointerenter={() => onhoverenter?.(item.annotation.id, volume)}
    onpointerleave={() => onhoverleave?.(item.annotation.id)}
>
    <T.BoxGeometry args={[...item.annotation.size]} />
    <T.MeshBasicMaterial />
</T.Mesh>
