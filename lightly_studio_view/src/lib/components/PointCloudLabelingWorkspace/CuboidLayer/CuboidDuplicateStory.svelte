<script lang="ts">
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import { writable } from 'svelte/store';
    import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidLayer from './CuboidLayer.svelte';

    type CuboidAnnotation = ReturnType<typeof createAnnotationFixture>;

    const classes = [{ id: 'vehicle', name: 'Vehicle', color: '#3b82f6' }];
    const bounds = { min: [-10, -10, -10], max: [10, 10, 10] } as const;
    const origin: CuboidAnnotation = {
        ...createAnnotationFixture(),
        id: 'dup-origin',
        center: [0, 0, 1]
    };
    const state = writable({ cuboids: [origin], selectedId: origin.id as string | null });
</script>

<div class="relative h-screen w-screen bg-black">
    <div
        class="absolute left-4 top-4 z-10 rounded bg-black/70 px-3 py-2 font-mono text-xs text-white"
    >
        <p class="mb-1 font-semibold text-white/60">
            Select a cuboid, then press Ctrl+D to duplicate
        </p>
        <p>Count: {$state.cuboids.length}</p>
    </div>
    <Canvas>
        <T.Color attach="background" args={['#10141c']} />
        <T.PerspectiveCamera position={[18, -22, 16]} makeDefault fov={50}>
            <OrbitControls target={[0, 0, 0]} enableDamping />
        </T.PerspectiveCamera>
        <T.AmbientLight intensity={1.5} />
        <T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
        <CuboidLayer
            cuboids={$state.cuboids}
            annotationClasses={classes}
            pointCloudBounds={bounds}
            selectedAnnotationId={$state.selectedId}
            hoveredAnnotationId={null}
            activeTool="select"
            onselect={(id) => state.update((current) => ({ ...current, selectedId: id }))}
            oncuboidcreate={(cuboid) =>
                state.update((current) => ({ ...current, cuboids: [...current.cuboids, cuboid] }))}
        />
    </Canvas>
</div>
