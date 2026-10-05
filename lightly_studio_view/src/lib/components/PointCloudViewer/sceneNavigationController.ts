import * as THREE from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { listenToSceneNavigation, type SceneNavigationAction } from './sceneNavigation';

interface Params {
    camera: THREE.PerspectiveCamera;
    controls: OrbitControls;
    invalidate: () => void;
}

export function createSceneNavigationController({ camera, controls, invalidate }: Params) {
    let navigationFrame: number | undefined;
    let navigationDamping = true;

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
            controls.enableDamping = navigationDamping;
        };

        navigationFrame = requestAnimationFrame(animate);
    }

    function cancelNavigationAnimation() {
        if (navigationFrame === undefined) return;
        cancelAnimationFrame(navigationFrame);
        navigationFrame = undefined;
        controls.enableDamping = navigationDamping;
    }

    const unsubscribe = listenToSceneNavigation(({ action, phase }) => {
        if (phase === 'step') navigateStep(action);
    });

    function navigateStep(action: SceneNavigationAction) {
        const targetPosition = camera.position.clone();
        const targetCenter = controls.target.clone();
        if (action === 'rotate-left' || action === 'rotate-right') {
            rotatePosition(targetPosition, targetCenter, action === 'rotate-left' ? 0.12 : -0.12);
        } else {
            const { direction, right } = getMovementAxes(targetPosition, targetCenter);
            const movements = {
                forward: direction,
                backward: direction.clone().negate(),
                left: right.clone().negate(),
                right
            };
            const move = movements[action].multiplyScalar(
                targetPosition.distanceTo(targetCenter) * 0.08
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

function getMovementAxes(position: THREE.Vector3, center: THREE.Vector3) {
    const direction = center.clone().sub(position);
    direction.z = 0;
    direction.normalize();
    const right = direction
        .clone()
        .cross(new THREE.Vector3(0, 0, 1))
        .normalize();
    return { direction, right };
}

function rotatePosition(position: THREE.Vector3, center: THREE.Vector3, angle: number) {
    const spherical = new THREE.Spherical().setFromVector3(position.clone().sub(center));
    spherical.theta += angle;
    position.copy(center).add(new THREE.Vector3().setFromSpherical(spherical));
}
