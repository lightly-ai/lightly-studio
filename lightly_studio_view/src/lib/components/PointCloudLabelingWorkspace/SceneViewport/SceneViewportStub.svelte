<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type SceneViewport from './SceneViewport.svelte';

    interface Props {
        onCuboidTransform?: ComponentProps<typeof SceneViewport>['onCuboidTransform'];
    }

    let { onCuboidTransform }: Props = $props();
</script>

<div data-testid="workspace-scene-viewport">
    <button
        onclick={() =>
            onCuboidTransform?.({
                annotationId: 'annotation-1',
                frameId: 'lidar-front',
                center: [2, 3, 4],
                rotation: [0, 0, 0, 1],
                size: [1, 1, 1]
            })}>Transform cuboid</button
    >
</div>
