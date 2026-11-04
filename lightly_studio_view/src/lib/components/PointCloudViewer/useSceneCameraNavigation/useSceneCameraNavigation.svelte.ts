import { useThrelte } from '@threlte/core';
import { createSceneNavigationController } from '../sceneNavigationController';
import type { SceneCameraNavigationParams } from './types';

/** Connects camera navigation and native pointer cleanup to the scene lifecycle. */
export function useSceneCameraNavigation(getOptions: () => SceneCameraNavigationParams): void {
    const { invalidate, renderer } = useThrelte();
    $effect(() => {
        const {
            camera: currentCamera,
            controls: controlsRef,
            isActive,
            navigationId
        } = getOptions();
        if (!currentCamera || !controlsRef || (isActive && !isActive())) return;
        const navigation = createSceneNavigationController({
            camera: currentCamera,
            controls: controlsRef,
            invalidate,
            isActive,
            navigationId
        });
        const canvas = renderer.domElement;
        const suppress = (event: Event) => event.preventDefault();
        canvas.addEventListener('contextmenu', suppress);
        canvas.addEventListener('pointerdown', navigation.cancel);
        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            canvas.removeEventListener('pointerdown', navigation.cancel);
            navigation.dispose();
        };
    });
}
