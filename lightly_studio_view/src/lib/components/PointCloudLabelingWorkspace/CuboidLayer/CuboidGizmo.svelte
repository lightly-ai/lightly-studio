<script lang="ts">
    import { useParentObject3D } from '@threlte/core';
    import { TransformControls } from '@threlte/extras';
    import type { TransformControls as ThreeTransformControls } from 'three/examples/jsm/controls/TransformControls.js';
    import { getCuboidGizmoOptions } from './cuboidTransform';
    import { useCuboidTransformControls } from './useCuboidTransformControls.svelte';
    import OrthographicRotationRing from './OrthographicRotationRing/OrthographicRotationRing.svelte';
    import type { CameraMode, Vector3 } from '../domain';

    interface Props extends Omit<Parameters<typeof useCuboidTransformControls>[0], 'getControls'> {
        mode: 'translate' | 'rotate' | 'scale';
        cameraMode: CameraMode;
        size: Vector3;
        enabled?: boolean;
    }

    let {
        mode,
        cameraMode,
        size,
        enabled = true,
        onTransformEnd,
        onInteractionStart,
        onInteractionCancel
    }: Props = $props();

    const parentObject3D = useParentObject3D();
    let controlsRef = $state<ThreeTransformControls | undefined>();
    const options = $derived(getCuboidGizmoOptions(mode, cameraMode));

    useCuboidTransformControls({
        getControls: () => controlsRef,
        onTransformEnd: (object, snapshot) => onTransformEnd?.(object, snapshot),
        onInteractionStart: () => onInteractionStart?.(),
        onInteractionCancel: () => onInteractionCancel?.()
    });
</script>

{#if mode === 'rotate' && cameraMode !== 'perspective'}
    {#if enabled}
        <OrthographicRotationRing
            {size}
            {onTransformEnd}
            {onInteractionStart}
            {onInteractionCancel}
        />
    {/if}
{:else}
    <TransformControls
        bind:controls={controlsRef}
        {enabled}
        {mode}
        space={options.space}
        showX={options.showX}
        showY={options.showY}
        showZ={options.showZ}
        size={0.75}
        autoPauseControls={true}
        object={parentObject3D.current}
    />
{/if}
