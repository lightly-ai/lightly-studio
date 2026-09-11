<script lang="ts">
    import { interactivity } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidInteractionListeners from './CuboidInteractionListeners.svelte';
    import CuboidLayerItem from './CuboidLayerItem.svelte';
    import type { CuboidCreationConfig } from './cuboidCreation';
    import { addCuboidDuplicateListeners } from './cuboidDuplication';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';

    interactivity();

    interface Props {
        cuboids: readonly Domain.CuboidAnnotation[];
        annotationClasses: readonly Domain.AnnotationClass[];
        pointCloudBounds: Domain.Bounds3;
        selectedAnnotationId?: string | null;
        hoveredAnnotationId?: string | null;
        activeTool?: Domain.WorkspaceTool;
        orbitControls?: ThreeOrbitControls;
        creation?: CuboidCreationConfig;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        oncuboidupdate?: (cuboid: Domain.CuboidAnnotation) => void;
        oncuboiddelete?: (annotationId: string) => void;
        oncuboidcreate?: (cuboid: Domain.CuboidAnnotation) => void;
    }

    let {
        cuboids,
        annotationClasses,
        pointCloudBounds,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        orbitControls,
        creation,
        onselect,
        onhover,
        oncuboidupdate,
        oncuboiddelete,
        oncuboidcreate
    }: Props = $props();

    const selectedAnnotation = $derived(cuboids.find((c) => c.id === selectedAnnotationId) ?? null);

    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    let cuboidClicked = false;

    $effect(() => {
        const next = createCuboidRenderItems(cuboids);
        renderCuboids = next;
        return () => disposeCuboidRenderItems(next);
    });

    $effect(() => {
        if (!oncuboidcreate) return;
        return addCuboidDuplicateListeners({
            selectedAnnotation,
            oncreate: oncuboidcreate,
            onselect
        });
    });
</script>

<CuboidInteractionListeners
    {activeTool}
    {pointCloudBounds}
    {selectedAnnotationId}
    {creation}
    {onselect}
    {oncuboiddelete}
    isCuboidClicked={() => cuboidClicked}
    resetCuboidClicked={() => (cuboidClicked = false)}
/>

{#each renderCuboids as item (item.annotation.id)}
    <CuboidLayerItem
        {item}
        {annotationClasses}
        {selectedAnnotationId}
        {hoveredAnnotationId}
        {activeTool}
        {orbitControls}
        {onselect}
        {onhover}
        {oncuboidupdate}
        onselected={() => (cuboidClicked = true)}
    />
{/each}
