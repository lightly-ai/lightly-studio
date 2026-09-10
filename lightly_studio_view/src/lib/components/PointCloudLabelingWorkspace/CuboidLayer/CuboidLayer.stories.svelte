<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import {
        createAnnotationFixture,
        createCuboidAnnotation
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
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
