<script lang="ts">
    import { useThrelte } from '@threlte/core';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { addCuboidCreationListeners, type CuboidCreationConfig } from './cuboidCreation';
    import { addCuboidSelectionListeners } from './cuboidSelection';

    interface Props {
        activeTool: Domain.WorkspaceTool;
        pointCloudBounds: Domain.Bounds3;
        creation?: CuboidCreationConfig;
        onselect?: (annotationId: string | null) => void;
        isCuboidClicked: () => boolean;
        resetCuboidClicked: () => void;
    }

    let {
        activeTool,
        pointCloudBounds,
        creation,
        onselect,
        isCuboidClicked,
        resetCuboidClicked
    }: Props = $props();

    const { renderer, camera, scene } = useThrelte();

    $effect(() => {
        return addCuboidSelectionListeners({
            canvas: renderer.domElement,
            activeTool,
            onselect,
            isCuboidClicked,
            resetCuboidClicked
        });
    });

    $effect(() => {
        if (!creation) return;
        return addCuboidCreationListeners({
            canvas: renderer.domElement,
            activeTool,
            getContext: () => ({ camera: camera.current, scene, renderer }),
            config: creation,
            pointCloudBounds
        });
    });
</script>
