<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import {
        createAnnotationFixture,
        createCuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { writable } from 'svelte/store';
    import CuboidLayer from './CuboidLayer.svelte';

    const classes = [
        { id: 'vehicle', name: 'Vehicle', color: '#3b82f6' },
        { id: 'gallery-0', name: 'Gallery 0', color: '#22d3ee' },
        { id: 'gallery-1', name: 'Gallery 1', color: '#a78bfa' },
        { id: 'gallery-2', name: 'Gallery 2', color: '#facc15' },
        { id: 'gallery-3', name: 'Gallery 3', color: '#fb7185' },
        { id: 'gallery-4', name: 'Gallery 4', color: '#4ade80' }
    ];
    const bounds = { min: [-10, -10, -10], max: [10, 10, 10] } as const;
    const vehicle = createAnnotationFixture();
    const placements = [
        { center: [-8, 0, 1], yawDegrees: 0, annotationClassId: 'gallery-0' },
        { center: [-4, 0, 1], yawDegrees: 45, annotationClassId: 'gallery-1' },
        { center: [0, 0, 1], yawDegrees: 90, annotationClassId: 'gallery-2' },
        { center: [4, 0, 1], yawDegrees: 135, annotationClassId: 'gallery-3' },
        { center: [8, 0, 1], yawDegrees: -45, annotationClassId: 'gallery-4' }
    ] as const;
    const multipleCuboids = placements.map(({ center, yawDegrees, annotationClassId }, index) => {
        const halfYaw = (yawDegrees * Math.PI) / 360;
        return createCuboidAnnotation({
            ...vehicle,
            id: `annotation-${index}`,
            annotationClassId,
            center,
            size: vehicle.size,
            rotation: [0, 0, Math.sin(halfYaw), Math.cos(halfYaw)],
            trackId: null,
            keyframeId: null
        });
    });

    // State for the interactive translate story. Shared across story mounts
    // (acceptable for single-story interactive testing in Storybook).
    const rotateState = writable({
        cuboids: [
            createCuboidAnnotation({
                ...createAnnotationFixture(),
                id: 'rotate-test',
                annotationClassId: 'vehicle',
                center: [0, 0, 1] as const,
                size: [4.5, 1.8, 1.5] as const,
                rotation: [0, 0, 0, 1] as const,
                trackId: null,
                keyframeId: null
            })
        ],
        selectedId: 'rotate-test' as string | null
    });

    const translateState = writable({
        cuboids: [
            createCuboidAnnotation({
                ...createAnnotationFixture(),
                id: 'translate-test',
                annotationClassId: 'vehicle',
                center: [0, 0, 1] as const,
                size: [4.5, 1.8, 1.5] as const,
                rotation: [0, 0, 0, 1] as const,
                trackId: null,
                keyframeId: null
            })
        ],
        selectedId: 'translate-test' as string | null
    });

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/CuboidLayer',
        component: CuboidLayer,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' },
        args: {
            annotationClasses: classes,
            pointCloudBounds: bounds,
            selectedAnnotationId: null,
            hoveredAnnotationId: null,
            activeTool: 'select' as const
        }
    });
</script>

{#snippet scene(args)}
    <div class="h-screen w-screen bg-black">
        <Canvas>
            <T.Color attach="background" args={['#10141c']} />
            <T.PerspectiveCamera position={[18, -22, 16]} makeDefault fov={50}>
                <OrbitControls target={[0, 0, 0]} enableDamping />
            </T.PerspectiveCamera>
            <T.AmbientLight intensity={1.5} />
            <T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
            <CuboidLayer {...args} />
        </Canvas>
    </div>
{/snippet}

{#snippet translateScene()}
    {@const c = $translateState.cuboids[0].center}
    <div class="relative h-screen w-screen bg-black">
        <div class="absolute left-4 top-4 z-10 rounded bg-black/70 px-3 py-2 font-mono text-xs text-white">
            <p class="mb-1 font-semibold text-white/60">Centre (drag to update)</p>
            <p>X: {c[0].toFixed(2)} &nbsp; Y: {c[1].toFixed(2)} &nbsp; Z: {c[2].toFixed(2)}</p>
        </div>
        <Canvas>
            <T.Color attach="background" args={['#10141c']} />
            <T.PerspectiveCamera position={[18, -22, 16]} makeDefault fov={50}>
                <OrbitControls target={[0, 0, 0]} enableDamping />
            </T.PerspectiveCamera>
            <T.AmbientLight intensity={1.5} />
            <T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
            <CuboidLayer
                cuboids={$translateState.cuboids}
                annotationClasses={classes}
                pointCloudBounds={bounds}
                selectedAnnotationId={$translateState.selectedId}
                hoveredAnnotationId={null}
                activeTool="translate"
                onselect={(id) => translateState.update((s) => ({ ...s, selectedId: id }))}
                oncuboidupdate={(updated) =>
                    translateState.update((s) => ({
                        ...s,
                        cuboids: s.cuboids.map((c) => (c.id === updated.id ? updated : c))
                    }))}
            />
        </Canvas>
    </div>
{/snippet}

{#snippet rotateScene()}
    {@const [qx, qy, qz, qw] = $rotateState.cuboids[0].rotation}
    <div class="relative h-screen w-screen bg-black">
        <div class="absolute left-4 top-4 z-10 rounded bg-black/70 px-3 py-2 font-mono text-xs text-white">
            <p class="mb-1 font-semibold text-white/60">Rotation (drag rings to update)</p>
            <p>X: {qx.toFixed(3)} &nbsp; Y: {qy.toFixed(3)} &nbsp; Z: {qz.toFixed(3)} &nbsp; W: {qw.toFixed(3)}</p>
        </div>
        <Canvas>
            <T.Color attach="background" args={['#10141c']} />
            <T.PerspectiveCamera position={[18, -22, 16]} makeDefault fov={50}>
                <OrbitControls target={[0, 0, 0]} enableDamping />
            </T.PerspectiveCamera>
            <T.AmbientLight intensity={1.5} />
            <T.GridHelper args={[24, 24, '#344054', '#202938']} rotation={[Math.PI / 2, 0, 0]} />
            <CuboidLayer
                cuboids={$rotateState.cuboids}
                annotationClasses={classes}
                pointCloudBounds={bounds}
                selectedAnnotationId={$rotateState.selectedId}
                hoveredAnnotationId={null}
                activeTool="rotate"
                onselect={(id) => rotateState.update((s) => ({ ...s, selectedId: id }))}
                oncuboidupdate={(updated) =>
                    rotateState.update((s) => ({
                        ...s,
                        cuboids: s.cuboids.map((c) => (c.id === updated.id ? updated : c))
                    }))}
            />
        </Canvas>
    </div>
{/snippet}

<Story
    name="Cuboid gallery"
    args={{ cuboids: multipleCuboids }}
    parameters={{
        docs: {
            description: {
                story: 'Five cuboids at varying yaw angles rendered as class-colored wireframes with heading arrows.'
            }
        }
    }}
    template={scene}
/>

<Story
    name="Selected cuboid"
    args={{ cuboids: multipleCuboids, selectedAnnotationId: 'annotation-2' }}
    parameters={{
        docs: {
            description: {
                story: 'The center cuboid is selected. A visual transform gizmo appears at its center and edges are brighter.'
            }
        }
    }}
    template={scene}
/>

<Story
    name="Hovered cuboid"
    args={{ cuboids: [multipleCuboids[2]], hoveredAnnotationId: multipleCuboids[2].id }}
    parameters={{
        docs: {
            description: {
                story: 'The cuboid hover tooltip shows annotation metadata at the cuboid center.'
            }
        }
    }}
    template={scene}
/>

<Story
    name="Translate (interactive)"
    parameters={{
        docs: {
            description: {
                story: 'Select the cuboid, switch to the translate tool, then drag the gizmo. The HUD shows the live centre coordinates updating on drag end.'
            }
        }
    }}
    template={translateScene}
/>

<Story
    name="Rotate (interactive)"
    parameters={{
        docs: {
            description: {
                story: 'Drag the blue Z ring to rotate the cuboid around its vertical axis. The HUD shows the yaw angle updating on drag end.'
            }
        }
    }}
    template={rotateScene}
/>
