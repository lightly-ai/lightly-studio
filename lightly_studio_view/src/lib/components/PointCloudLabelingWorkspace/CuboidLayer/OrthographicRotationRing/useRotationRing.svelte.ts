import { useParentObject3D, useThrelte } from '@threlte/core';
import { useOrbitControls, type IntersectionEvent } from '@threlte/extras';
import { onMount } from 'svelte';
import { writable } from 'svelte/store';
import { restoreTransformSnapshot } from '../cuboidTransform';
import type { useCuboidTransformControls } from '../useCuboidTransformControls.svelte';
import { applyRotationDrag, createRotationDrag } from './rotationRing';

type Params = Omit<Parameters<typeof useCuboidTransformControls>[0], 'getControls'>;

export function useRotationRing(params: Params) {
    const { camera, renderer, invalidate } = useThrelte();
    const parent = useParentObject3D();
    const orbitControls = useOrbitControls();
    const canvas = renderer.domElement;
    const hovered = writable(false);
    let drag: ReturnType<typeof createRotationDrag> | null = null;
    let changed = false;
    let orbitEnabled = true;

    function onPointerDown(
        event: Pick<IntersectionEvent<PointerEvent>, 'nativeEvent' | 'stopPropagation'>
    ): void {
        if (event.nativeEvent.button !== 0 || !parent.current || drag) return;
        event.stopPropagation();
        params.onInteractionStart?.();
        drag = createRotationDrag({
            object: parent.current,
            camera: camera.current,
            canvas,
            event: event.nativeEvent
        });
        changed = false;
        canvas.setPointerCapture(drag.pointerId);
        canvas.style.cursor = 'grabbing';
        if (!orbitControls.current) return;
        orbitEnabled = orbitControls.current.enabled;
        orbitControls.current.enabled = false;
    }

    function setHovered(value: boolean): void {
        if (drag) return;
        hovered.set(value);
        canvas.style.cursor = value ? 'grab' : '';
    }

    function update(event: PointerEvent): void {
        if (!drag) return;
        changed = applyRotationDrag(drag, event);
        invalidate();
    }

    function finish(cancelled: boolean): void {
        const current = drag;
        if (!current) return;
        drag = null;
        if (canvas.hasPointerCapture(current.pointerId))
            canvas.releasePointerCapture(current.pointerId);
        if (orbitControls.current) orbitControls.current.enabled = orbitEnabled;
        setHovered(false);
        if (cancelled) restoreTransformSnapshot(current.object, current.snapshot);
        if (!cancelled && changed) params.onTransformEnd?.(current.object, current.snapshot);
        else params.onInteractionCancel?.();
        invalidate();
    }

    function onPointerMove(event: PointerEvent): void {
        if (event.pointerId !== drag?.pointerId) return;
        event.stopImmediatePropagation();
        update(event);
        if (event.buttons === 0) finish(false);
    }

    function onPointerUp(event: PointerEvent): void {
        if (event.pointerId !== drag?.pointerId) return;
        // Let the event reach the orbit controls' document listener so they drop the
        // pointer they started tracking on pointerdown.
        update(event);
        finish(false);
    }

    function onPointerCancel(event: PointerEvent): void {
        if (event.pointerId === drag?.pointerId) finish(true);
    }

    function onKeyDown(event: KeyboardEvent): void {
        if (event.key !== 'Escape' || !drag) return;
        event.stopImmediatePropagation();
        event.preventDefault();
        finish(true);
    }

    function onBlur(): void {
        finish(true);
    }

    onMount(() => {
        canvas.addEventListener('pointermove', onPointerMove, true);
        canvas.addEventListener('pointerup', onPointerUp, true);
        canvas.addEventListener('pointercancel', onPointerCancel, true);
        canvas.addEventListener('lostpointercapture', onPointerCancel, true);
        window.addEventListener('keydown', onKeyDown, true);
        window.addEventListener('blur', onBlur);
        return () => {
            canvas.removeEventListener('pointermove', onPointerMove, true);
            canvas.removeEventListener('pointerup', onPointerUp, true);
            canvas.removeEventListener('pointercancel', onPointerCancel, true);
            canvas.removeEventListener('lostpointercapture', onPointerCancel, true);
            window.removeEventListener('keydown', onKeyDown, true);
            window.removeEventListener('blur', onBlur);
            finish(true);
            canvas.style.cursor = '';
        };
    });

    return { hovered, onPointerDown, setHovered };
}
