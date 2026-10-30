<script lang="ts">
    import { T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import * as THREE from 'three';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import type {
        CameraMode,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    /** Camera projection and interaction bindings for a point-cloud scene. */
    interface Props {
        /** Projection orientation to render. */
        cameraMode: CameraMode;
        /** Editing tool controlling which camera gestures are allowed. */
        activeTool: WorkspaceTool;
        /** Instantiated camera shared with fitting and navigation. */
        camera?: THREE.PerspectiveCamera | THREE.OrthographicCamera;
        /** Orbit controls attached to this camera. */
        controls?: ThreeOrbitControls;
    }
    let { cameraMode, activeTool, camera = $bindable(), controls = $bindable() }: Props = $props();
    let perspectiveCamera = $state<THREE.PerspectiveCamera>();
    let orthographicCamera = $state<THREE.OrthographicCamera>();
    $effect.pre(() => {
        camera = cameraMode === 'perspective' ? perspectiveCamera : orthographicCamera;
    });
</script>

{#if cameraMode === 'perspective'}
    <T.PerspectiveCamera
        bind:ref={perspectiveCamera}
        makeDefault
        fov={60}
        near={0.1}
        far={10000}
        up={[0, 0, 1]}
    >
        <OrbitControls
            bind:ref={controls}
            enableDamping
            enableRotate={activeTool !== 'create-cuboid'}
            screenSpacePanning={false}
            mouseButtons={{
                LEFT: THREE.MOUSE.ROTATE,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN
            }}
            touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE }}
        />
    </T.PerspectiveCamera>
{:else}
    <T.OrthographicCamera
        bind:ref={orthographicCamera}
        makeDefault
        manual
        left={-1}
        right={1}
        top={1}
        bottom={-1}
        near={0.1}
        far={10000}
        up={cameraMode === 'top' ? [0, 1, 0] : [0, 0, 1]}
    >
        <OrbitControls
            bind:ref={controls}
            enableDamping
            enableRotate={false}
            screenSpacePanning
            mouseButtons={{
                LEFT: activeTool === 'create-cuboid' ? undefined : THREE.MOUSE.PAN,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN
            }}
            touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN }}
        />
    </T.OrthographicCamera>
{/if}
