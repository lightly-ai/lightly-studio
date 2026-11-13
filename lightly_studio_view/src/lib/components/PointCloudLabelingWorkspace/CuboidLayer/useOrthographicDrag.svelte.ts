import { useParentObject3D, useThrelte } from '@threlte/core';
import { useOrbitControls, type IntersectionEvent } from '@threlte/extras';
import { onMount } from 'svelte';
import { writable } from 'svelte/store';
import type { Camera, Object3D } from 'three';
import { captureTransformSnapshot, restoreTransformSnapshot } from './cuboidTransform';
import type { useCuboidTransformControls } from './useCuboidTransformControls.svelte';

type Params = Omit<Parameters<typeof useCuboidTransformControls>[0], 'getControls'>;

interface Drag {
    object: Object3D;
    pointerId: number;
    snapshot: ReturnType<typeof captureTransformSnapshot>;
}

interface DragKind<TDrag extends Drag> {
    create: (args: {
        object: Object3D;
        camera: Camera;
        canvas: HTMLCanvasElement;
        event: PointerEvent;
    }) => TDrag;
    /** Applies the pointer position to the object and reports whether it changed. */
    apply: (drag: TDrag, event: PointerEvent) => boolean;
}

/**
 * Runs a pointer drag on the parent object of an orthographic view handle: captures the
 * pointer, pauses camera controls, and commits on release or restores on cancel.
 */
export function useOrthographicDrag<TDrag extends Drag>(params: Params, kind: DragKind<TDrag>) {
    const { camera, renderer, invalidate } = useThrelte();
    const parent = useParentObject3D();
    const orbitControls = useOrbitControls();
    const canvas = renderer.domElement;
    const hovered = writable(false);
    let drag: TDrag | null = null;
    let changed = false;
    let orbitEnabled = true;

    function onPointerDown(
        event: Pick<IntersectionEvent<PointerEvent>, 'nativeEvent' | 'stopPropagation'>
    ): void {
        if (event.nativeEvent.button !== 0 || !parent.current || drag) return;
        event.stopPropagation();
        // Keep TransformControls on the same element from taking pointer capture.
        event.nativeEvent.stopImmediatePropagation();
        params.onInteractionStart?.();
        drag = kind.create({
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
        changed = kind.apply(drag, event);
        if (changed) params.onTransformPreview?.(drag.object);
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
