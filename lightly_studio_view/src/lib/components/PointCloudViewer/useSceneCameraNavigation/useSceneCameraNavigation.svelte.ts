import { useThrelte } from '@threlte/core';
import { createOrbitTargetAnchor } from '../orbitTargetAnchor';
import { createSceneNavigationController } from '../sceneNavigationController';
import { enableScreenSpacePanning } from '../screenSpacePanning';
import type { SceneCameraNavigationParams } from './types';

/** Connects camera navigation and native pointer cleanup to the scene lifecycle. */
export function useSceneCameraNavigation(getOptions: () => SceneCameraNavigationParams): void {
    const { invalidate, renderer, scene } = useThrelte();
    $effect(() => {
        const {
            camera: currentCamera,
            controls: controlsRef,
            isActive,
            navigationId
        } = getOptions();
        if (!currentCamera || !controlsRef || (isActive && !isActive())) return;
        const isPerspective = 'isPerspectiveCamera' in currentCamera;
        const targetAnchor = isPerspective
            ? createOrbitTargetAnchor(controlsRef, scene)
            : undefined;
        const restorePanning = isPerspective ? enableScreenSpacePanning(controlsRef) : undefined;
        const navigation = createSceneNavigationController({
            camera: currentCamera,
            controls: controlsRef,
            invalidate,
            isActive,
            navigationId,
            anchorTarget: targetAnchor?.anchor
        });
        const canvas = renderer.domElement;
        const suppress = (event: Event) => event.preventDefault();
        canvas.addEventListener('contextmenu', suppress);
        canvas.addEventListener('pointerdown', navigation.cancel);
        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            canvas.removeEventListener('pointerdown', navigation.cancel);
            navigation.dispose();
            restorePanning?.();
            targetAnchor?.dispose();
        };
    });
}
