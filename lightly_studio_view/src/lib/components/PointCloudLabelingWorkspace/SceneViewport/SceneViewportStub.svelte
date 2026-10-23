<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type SceneViewport from './SceneViewport.svelte';
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

    interface Props {
        transforms: ComponentProps<typeof SceneViewport>['transforms'];
    }

    let { transforms }: Props = $props();

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
