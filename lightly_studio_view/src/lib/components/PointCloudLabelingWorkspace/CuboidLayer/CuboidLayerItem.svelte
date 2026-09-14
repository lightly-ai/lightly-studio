<script lang="ts">
    import { T } from '@threlte/core';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import CuboidResizeGizmo from './CuboidResizeGizmo.svelte';
    import CuboidTooltip from './CuboidTooltip/CuboidTooltip.svelte';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidRenderItems } from './cuboidRenderItems';

    interface Props {
        item: ReturnType<typeof createCuboidRenderItems>[number];
        annotationClasses: readonly Domain.AnnotationClass[];
        selectedAnnotationId: string | null;
        hoveredAnnotationId: string | null;
        activeTool: Domain.WorkspaceTool;
        orbitControls?: ThreeOrbitControls;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        oncuboidupdate?: (cuboid: Domain.CuboidAnnotation) => void;
        onselected: () => void;
    }

    let {
        item,
        annotationClasses,
        selectedAnnotationId,
        hoveredAnnotationId,
        activeTool,
        orbitControls,
        onselect,
        onhover,
        oncuboidupdate,
        onselected
    }: Props = $props();

    let resizePreviewAnnotation = $state<Domain.CuboidAnnotation | null>(null);
    const base = $derived(resolveCuboidColor(annotationClasses, item.annotation.annotationClassId));
    const annotationClassName = $derived(
        annotationClasses.find(({ id }) => id === item.annotation.annotationClassId)?.name ??
            item.annotation.annotationClassId
    );
    const isSelected = $derived(selectedAnnotationId === item.annotation.id);
    const isHovered = $derived(hoveredAnnotationId === item.annotation.id);
    const color = $derived(highlightCuboidColor(base, isSelected, isHovered));
</script>

{#snippet visual()}
    <CuboidVisual
        {item}
        baseColor={base}
        edgeColor={color}
        {activeTool}
        {onselect}
        {onhover}
        {onselected}
    />
    {#if isHovered}
        <CuboidTooltip {annotationClassName} annotation={item.annotation} />
    {/if}
{/snippet}

{#if isSelected && activeTool === 'resize'}
    <CuboidGizmo
        annotation={resizePreviewAnnotation ?? item.annotation}
        activeTool="translate"
        enabled={false}
    />
    <CuboidResizeGizmo
        annotation={item.annotation}
        baseColor={base}
        edgeColor={color}
        {orbitControls}
        {onhover}
        {oncuboidupdate}
        onliveupdate={(annotation) => (resizePreviewAnnotation = annotation)}
    />
    {#if isHovered}
        <T.Group position={[...item.annotation.center]} quaternion={[...item.annotation.rotation]}>
            <CuboidTooltip {annotationClassName} annotation={item.annotation} />
        </T.Group>
    {/if}
{:else if isSelected}
    <CuboidGizmo annotation={item.annotation} {activeTool} {oncuboidupdate}>
        {@render visual()}
    </CuboidGizmo>
{:else}
    <T.Group position={[...item.annotation.center]} quaternion={[...item.annotation.rotation]}>
        {@render visual()}
    </T.Group>
{/if}
