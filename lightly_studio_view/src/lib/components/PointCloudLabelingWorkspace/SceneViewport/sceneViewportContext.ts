import { getContext, setContext } from 'svelte';
import type { resolveSceneViewportProps } from './resolveSceneViewportProps';
import type { useSceneViewport } from './useSceneViewport/useSceneViewport.svelte';
/** Values shared between a viewport's canvas and HTML overlay. */
interface ViewportContext {
    /** Reads current rendering inputs. */
    getProps: () => ReturnType<typeof resolveSceneViewportProps>;
    /** Activation, navigation, and cursor state for this viewport. */
    interaction: ReturnType<typeof useSceneViewport>;
}
const KEY = Symbol('scene-viewport');
/** Provides state to the viewport's rendering children. */
export function provideSceneViewportContext(context: ViewportContext): void {
    setContext(KEY, context);
}
/** Reads the nearest viewport's state. */
export function useSceneViewportContext(): ViewportContext {
    const context = getContext<ViewportContext | undefined>(KEY);
    if (!context) throw new Error('Scene viewport context is missing.');
    return context;
}
