import { getContext, setContext } from 'svelte';

const KEY = Symbol('annotation-tree-enabled');

/** Lets the Images grid and image sample details know that the annotation tree is on. */
export const setAnnotationTreeEnabled = (isEnabled: () => boolean) => setContext(KEY, isEnabled);

export const getAnnotationTreeEnabled = (): (() => boolean) =>
    getContext<(() => boolean) | undefined>(KEY) ?? (() => false);
