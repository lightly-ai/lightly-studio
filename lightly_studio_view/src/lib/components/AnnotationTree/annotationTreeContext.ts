import { getContext, setContext } from 'svelte';

const KEY = Symbol('annotation-tree-enabled');

/** Lets the grid pages know that the layout shows the annotation tree. */
export const setAnnotationTreeEnabled = (isEnabled: () => boolean) => setContext(KEY, isEnabled);

export const getAnnotationTreeEnabled = (): (() => boolean) =>
    getContext<(() => boolean) | undefined>(KEY) ?? (() => false);
