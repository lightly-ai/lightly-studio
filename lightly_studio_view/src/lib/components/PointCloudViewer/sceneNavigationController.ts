import * as THREE from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { listenToSceneNavigation, type SceneNavigationAction } from './sceneNavigation';
import { getMovementAxes, getNavigationDistance, rotatePosition } from './sceneNavigationMovement';

/** Dependencies for navigation input routing and animation lifecycle. */
interface Params {
    /** Camera whose position and projection are controlled. */
    camera: THREE.PerspectiveCamera | THREE.OrthographicCamera;
    /** Orbit controls supplying the shared scene target. */
    controls: OrbitControls;
    /** Requests a render after camera or geometry changes. */
    invalidate: () => void;
    /** Whether this viewport currently owns navigation input. */
    isActive?: () => boolean;
    /** Identifies the viewport receiving navigation commands. */
    navigationId?: symbol;
}

/** Animates navigation commands addressed to one viewport and cleans up on disposal. */
export function createSceneNavigationController({
    camera,
    controls,
    invalidate,
    isActive,
    navigationId
}: Params) {
    let navigationFrame: number | undefined;
    let navigationDamping = true;
    let lastContinuousNavigationTime = 0;
    const continuousNavigation = new Map<SceneNavigationAction, number>();

    function animateContinuousNavigation(now: number) {
        if (continuousNavigation.size === 0) {
            navigationFrame = undefined;
            controls.enableDamping = navigationDamping;
            return;
        }

        const delta = Math.min((now - lastContinuousNavigationTime) / 1000, 0.05);
        lastContinuousNavigationTime = now;
        moveContinuously(delta);

        controls.update();
        invalidate();
        navigationFrame = requestAnimationFrame(animateContinuousNavigation);
    }

    function moveContinuously(delta: number) {
        const { direction, right } = getMovementAxes(camera, camera.position, controls.target);
        const move = new THREE.Vector3();
        if (continuousNavigation.has('forward')) move.add(direction);
        if (continuousNavigation.has('backward')) move.sub(direction);
        if (continuousNavigation.has('right')) move.add(right);
        if (continuousNavigation.has('left')) move.sub(right);
        move.multiplyScalar(getNavigationDistance(camera, controls.target) * 0.85 * delta);
        camera.position.add(move);
        controls.target.add(move);
        const rotateLeft = continuousNavigation.has('rotate-left');
        const rotateRight = continuousNavigation.has('rotate-right');
        if (rotateLeft !== rotateRight) {
            rotatePosition(camera.position, controls.target, (rotateLeft ? 1 : -1) * 0.9 * delta);
        }
    }

    function animateNavigation(targetPosition: THREE.Vector3, targetCenter: THREE.Vector3) {
        if (navigationFrame === undefined) navigationDamping = controls.enableDamping;
        else cancelAnimationFrame(navigationFrame);

        controls.enableDamping = false;
        const startPosition = camera.position.clone();
        const startCenter = controls.target.clone();
        const startedAt = performance.now();
        const duration = 180;

        const animate = (now: number) => {
            const progress = Math.min((now - startedAt) / duration, 1);
            const eased = 1 - (1 - progress) ** 3;
            camera.position.lerpVectors(startPosition, targetPosition, eased);
            controls.target.lerpVectors(startCenter, targetCenter, eased);
            controls.update();
            invalidate();

            if (progress < 1) {
                navigationFrame = requestAnimationFrame(animate);
                return;
            }
            navigationFrame = undefined;
            if (continuousNavigation.size > 0) {
                lastContinuousNavigationTime = performance.now();
                navigationFrame = requestAnimationFrame(animateContinuousNavigation);
            } else controls.enableDamping = navigationDamping;
        };

        navigationFrame = requestAnimationFrame(animate);
    }

    function cancelNavigationAnimation() {
        continuousNavigation.clear();
        if (navigationFrame === undefined) return;
        cancelAnimationFrame(navigationFrame);
        navigationFrame = undefined;
        controls.enableDamping = navigationDamping;
    }

    const unsubscribe = listenToSceneNavigation(({ action, phase, navigationId: eventId }) => {
        if (eventId !== navigationId) return;
        if (phase !== 'stop' && isActive && !isActive()) return;
        if (camera instanceof THREE.OrthographicCamera && action.startsWith('rotate-')) return;
        if (phase === 'start') {
            if (navigationFrame === undefined) navigationDamping = controls.enableDamping;
            else cancelAnimationFrame(navigationFrame);
            continuousNavigation.set(action, (continuousNavigation.get(action) ?? 0) + 1);
            controls.enableDamping = false;
            lastContinuousNavigationTime = performance.now();
            navigationFrame = requestAnimationFrame(animateContinuousNavigation);
            return;
        }
        if (phase === 'stop') {
            const count = continuousNavigation.get(action) ?? 0;
            if (count > 1) continuousNavigation.set(action, count - 1);
            else continuousNavigation.delete(action);
            return;
        }

        navigateStep(action);
    });

    function navigateStep(action: SceneNavigationAction) {
        const targetPosition = camera.position.clone();
        const targetCenter = controls.target.clone();
        if (action === 'rotate-left' || action === 'rotate-right') {
            rotatePosition(targetPosition, targetCenter, action === 'rotate-left' ? 0.12 : -0.12);
        } else {
            const { direction, right } = getMovementAxes(camera, targetPosition, targetCenter);
            const movements = {
                forward: direction,
                backward: direction.clone().negate(),
                left: right.clone().negate(),
                right
            };
            const move = movements[action].multiplyScalar(
                getNavigationDistance(camera, controls.target) * 0.08
            );
            targetPosition.add(move);
            targetCenter.add(move);
        }
        animateNavigation(targetPosition, targetCenter);
    }

    return {
        cancel: cancelNavigationAnimation,
        dispose: () => {
            unsubscribe();
            cancelNavigationAnimation();
        }
    };
}
