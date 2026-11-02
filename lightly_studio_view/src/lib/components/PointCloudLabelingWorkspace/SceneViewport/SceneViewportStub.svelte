<script lang="ts">
    import type { ComponentProps, Snippet } from 'svelte';
    import type SceneViewport from './SceneViewport.svelte';
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

    /** Minimal renderer retaining workspace content without creating a WebGL canvas. */
    interface Props {
        /** Shared transform state used to exercise annotation persistence. */
        transforms: ComponentProps<typeof SceneViewport>['transforms'];
        /** Header content supplied by the workspace. */
        header?: Snippet;
        /** Editing toolbar supplied by the main viewport. */
        tools?: Snippet;
    }

    let { transforms, header, tools }: Props = $props();

    // Minimal annotation used to seed the transform state before committing.
    const stubAnnotation: CuboidAnnotation = {
        id: 'annotation-1',
        frameId: 'lidar-front',
        coordinateFrame: {
            id: 'ego',
            convention: 'right-handed-x-forward-y-left-z-up',
            unit: 'meter'
        },
        annotationClassId: 'class-1',
        annotationSourceId: 'source-1',
        trackId: null,
        trackNumber: null,
        parentTrackNumber: null,
        keyframeId: null,
        center: [0, 0, 0],
        size: [1, 1, 1],
        rotation: [0, 0, 0, 1]
    };
</script>

<div data-testid="workspace-scene-viewport">
    {@render header?.()}
    {@render tools?.()}
    <button
        onclick={() => {
            transforms.reconcile([stubAnnotation]);
            void transforms.commit({
                annotationId: 'annotation-1',
                frameId: 'lidar-front',
                center: [2, 3, 4],
                rotation: [0, 0, 0, 1],
                size: [1, 1, 1]
            });
        }}>Transform cuboid</button
    >
</div>
