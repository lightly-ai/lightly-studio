<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import * as THREE from 'three';
    import { fn } from 'storybook/test';
    import CuboidDraftPlayground from './CuboidDraftPlayground.svelte';

    /** Points on the faces of a box that is turned around the vertical axis. */
    function createObjectPoints(
        center: [number, number],
        size: [number, number, number],
        yawDegrees: number
    ): number[] {
        const yaw = (yawDegrees * Math.PI) / 180;
        const points: number[] = [];
        const steps = 14;
        for (let i = 0; i <= steps; i++) {
            for (let j = 0; j <= steps; j++) {
                const u = i / steps - 0.5;
                const v = j / steps;
                // Two long faces, two short faces and the roof.
                const local = [
                    [u * size[0], -size[1] / 2, v * size[2]],
                    [u * size[0], size[1] / 2, v * size[2]],
                    [-size[0] / 2, u * size[1], v * size[2]],
                    [size[0] / 2, u * size[1], v * size[2]],
                    [u * size[0], (v - 0.5) * size[1], size[2]]
                ];
                for (const [x, y, z] of local) {
                    points.push(
                        center[0] + x * Math.cos(yaw) - y * Math.sin(yaw),
                        center[1] + x * Math.sin(yaw) + y * Math.cos(yaw),
                        z
                    );
                }
            }
        }
        return points;
    }

    const positions = new Float32Array([
        ...createObjectPoints([-4, 2], [4.2, 1.8, 1.5], 30),
        ...createObjectPoints([3, -2], [4.6, 2, 1.7], -20),
        ...createObjectPoints([2, 4], [0.7, 0.7, 1.8], 0)
    ]);
    const batch = {
        positions,
        intensities: new Float32Array(positions.length / 3),
        count: positions.length / 3
    };
    const bounds = { min: [-8, -8, 0], max: [8, 8, 2] } as const;
    const cameraPositions = {
        top: [0, 0, 30],
        side: [30, 0, 1],
        front: [0, -30, 1]
    } as const;

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/CuboidDraftTarget',
        component: CuboidDraftPlayground,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' },
        args: { batch, bounds, onCreateCuboid: fn() }
    });
</script>

{#snippet template(args)}
    <div class="h-screen w-screen cursor-crosshair bg-black">
        <Canvas>
            {#if args.cameraMode === 'perspective'}
                <T.PerspectiveCamera makeDefault position={[10, -14, 9]} fov={50} up={[0, 0, 1]}>
                    <!-- As in the workspace, the left button is free for drawing. -->
                    <OrbitControls
                        target={[0, 0, 0]}
                        mouseButtons={{ MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE }}
                    />
                </T.PerspectiveCamera>
            {:else}
                <T.OrthographicCamera
                    makeDefault
                    position={[...cameraPositions[args.cameraMode]]}
                    zoom={40}
                    up={args.cameraMode === 'top' ? [0, 1, 0] : [0, 0, 1]}
                >
                    <OrbitControls
                        target={[0, 0, args.cameraMode === 'top' ? 0 : 1]}
                        enableRotate={false}
                        mouseButtons={{ MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN }}
                    />
                </T.OrthographicCamera>
            {/if}
            <CuboidDraftPlayground {...args} />
        </Canvas>
    </div>
{/snippet}

<Story
    name="Perspective view"
    args={{ cameraMode: 'perspective' }}
    parameters={{
        docs: {
            description: {
                story: 'Press on the ground and drag along one side of an object, then release. Move the mouse and click to set the width. Move the mouse and click to set the height. Escape or a right-click cancels. The right button turns the camera.'
            }
        }
    }}
    {template}
/>

<Story
    name="Top view"
    args={{ cameraMode: 'top' }}
    parameters={{
        docs: {
            description: {
                story: 'Drag along one side of an object and release, then move the mouse and click to set the width. The height is fitted to the points inside the footprint.'
            }
        }
    }}
    {template}
/>

<Story
    name="Side view"
    args={{ cameraMode: 'side' }}
    parameters={{
        docs: {
            description: {
                story: 'One drag draws a rectangle. The depth is fitted to the points inside it.'
            }
        }
    }}
    {template}
/>

<Story
    name="Front view"
    args={{ cameraMode: 'front' }}
    parameters={{
        docs: {
            description: {
                story: 'One drag draws a rectangle. The depth is fitted to the points inside it.'
            }
        }
    }}
    {template}
/>
