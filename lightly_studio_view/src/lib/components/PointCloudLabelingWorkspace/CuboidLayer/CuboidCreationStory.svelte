<script lang="ts">
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import * as THREE from 'three';
    import { writable } from 'svelte/store';
    import {
        canonicalCoordinateFrame,
        createCuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidLayer from './CuboidLayer.svelte';

    const classes = [{ id: 'vehicle', name: 'Vehicle', color: '#3b82f6' }];
    const bounds = { min: [-10, -10, -10], max: [10, 10, 10] } as const;
    const state = writable({ cuboids: [] as ReturnType<typeof createCuboidAnnotation>[] });
    const coordinateFrame = canonicalCoordinateFrame('lidar-0');
    const groundGeometry = createGroundGeometry();
    const count = $derived($state.cuboids.length);
    const last = $derived($state.cuboids.at(-1));

    function createGroundGeometry(): THREE.BufferGeometry {
        const count = 40_000;
        const positions = new Float32Array(count * 3);
        for (let index = 0; index < count; index++) {
            positions[index * 3] = (Math.random() - 0.5) * 20;
            positions[index * 3 + 1] = (Math.random() - 0.5) * 20;
        }
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        return geometry;
    }
</script>

<div class="relative h-screen w-screen bg-black">
    <div
        class="absolute left-4 top-4 z-10 rounded bg-black/70 px-3 py-2 font-mono text-xs text-white"
    >
        <p class="mb-1 font-semibold text-white/60">Click the ground plane to place a cuboid</p>
        <p>Placed: {count}</p>
        {#if last}
            {@const [x, y, z] = last.center}
            <p>Last: X: {x.toFixed(2)} &nbsp; Y: {y.toFixed(2)} &nbsp; Z: {z.toFixed(2)}</p>
        {/if}
    </div>
    <Canvas>
        <T.Color attach="background" args={['#10141c']} />
        <T.PerspectiveCamera position={[0, -28, 18]} makeDefault fov={50}>
            <OrbitControls target={[0, 0, 0]} enableDamping />
        </T.PerspectiveCamera>
        <T.AmbientLight intensity={1.5} />
        <T.Points geometry={groundGeometry}>
            <T.PointsMaterial color="#94a3b8" size={2} sizeAttenuation={false} />
        </T.Points>
        <CuboidLayer
            cuboids={$state.cuboids}
            annotationClasses={classes}
            pointCloudBounds={bounds}
            activeTool="create-cuboid"
            creation={{
                annotationClassId: 'vehicle',
                frameId: 'frame-0',
                coordinateFrame,
                annotationSourceId: 'ground-truth',
                oncreate: (cuboid) =>
                    state.update((current) => ({
                        cuboids: [
                            ...current.cuboids,
                            createCuboidAnnotation({
                                ...cuboid,
                                id: `created-${current.cuboids.length}`
                            })
                        ]
                    }))
            }}
        />
    </Canvas>
</div>
