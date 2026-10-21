<script lang="ts">
    import { T } from '@threlte/core';
    import type { IntersectionEvent } from '@threlte/extras';
    import { Color, DoubleSide } from 'three';
    import { FACE_DEFINITIONS, getCuboidFaceLayout } from './cuboidFaceResize';
    import { useCuboidFaceResize } from './useCuboidFaceResize';
    import { CuboidResizeHandle } from './CuboidResizeHandle';

    interface Props extends Pick<
        Parameters<typeof useCuboidFaceResize>[0],
        'onResizeStart' | 'onResizeEnd'
    > {
        annotation: ReturnType<Parameters<typeof useCuboidFaceResize>[0]['getAnnotation']>;
        baseColor: string;
    }

    let { annotation, baseColor, onResizeStart, onResizeEnd }: Props = $props();
    const { hoveredFace, onFaceHoverEnter, onFaceHoverLeave, onFacePointerDown } =
        useCuboidFaceResize({
            getAnnotation: () => annotation,
            onResizeStart: () => onResizeStart?.(),
            onResizeEnd: (payload) => onResizeEnd?.(payload)
        });
    const highlightColor = $derived(new Color(baseColor).lerp(new Color(0xffffff), 0.65));
</script>

{#each FACE_DEFINITIONS as face}
    {@const { position, planeSize } = getCuboidFaceLayout({ face, size: annotation.size })}

    <!-- Invisible hit-test plane: always raycasted, owns all pointer events -->
    <T.Mesh
        {position}
        rotation={[...face.euler]}
        onpointerenter={(event: IntersectionEvent<PointerEvent>) => {
            event.stopPropagation();
            onFaceHoverEnter(face);
        }}
        onpointerleave={onFaceHoverLeave}
        onpointerdown={(event: IntersectionEvent<PointerEvent>) => {
            event.stopPropagation();
            onFacePointerDown({ event, face });
        }}
    >
        <T.PlaneGeometry args={planeSize} />
        <T.MeshBasicMaterial opacity={0} transparent={true} depthWrite={false} side={DoubleSide} />
    </T.Mesh>

    <!-- Visible highlight: raycast disabled so it never steals events from adjacent faces -->
    {#if $hoveredFace === face}
        <T.Mesh {position} rotation={[...face.euler]} raycast={() => {}}>
            <T.PlaneGeometry args={planeSize} />
            <T.MeshBasicMaterial
                color={highlightColor}
                opacity={0.5}
                transparent={true}
                depthWrite={false}
                side={DoubleSide}
            />
        </T.Mesh>
    {/if}

    <!-- Persistent gizmo handle: arrow shaft + box cap, always visible in resize mode -->
    <CuboidResizeHandle
        {position}
        euler={face.euler}
        axisIndex={face.axis}
        isActive={$hoveredFace === face}
        onpointerenter={() => {
            onFaceHoverEnter(face);
        }}
        onpointerleave={onFaceHoverLeave}
        onpointerdown={(event) => {
            event.stopPropagation();
            onFacePointerDown({ event, face });
        }}
    />
{/each}
