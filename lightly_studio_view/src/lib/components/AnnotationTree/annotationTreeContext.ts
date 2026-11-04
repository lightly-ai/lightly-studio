import { getContext, setContext } from 'svelte';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

const KEY = Symbol('annotation-tree-enabled');

/** Lets the Images grid and image sample details know that the annotation tree is on. */
export const setAnnotationTreeEnabled = (isEnabled: () => boolean) => setContext(KEY, isEnabled);

export const getAnnotationTreeEnabled = (): (() => boolean) =>
    getContext<(() => boolean) | undefined>(KEY) ?? (() => false);

const FLAT_TREE_KEY = Symbol('flat-annotation-tree-collection-id');

/**
 * Lets the Annotations page know the images collection whose tree it follows. It is undefined
 * while the tree is off.
 */
export const setFlatAnnotationTreeCollectionId = (getId: () => string | undefined) =>
    setContext(FLAT_TREE_KEY, getId);

export const getFlatAnnotationTreeCollectionId = (): (() => string | undefined) =>
    getContext<(() => string | undefined) | undefined>(FLAT_TREE_KEY) ?? (() => undefined);

type IsAnnotationVisible = (annotation: AnnotationView) => boolean;

const VISIBILITY_KEY = Symbol('annotation-tree-visibility');

/** Lets the tiles of the Annotations grid follow the tree eyes, which are undefined when off. */
export const setTreeAnnotationVisibility = (get: () => IsAnnotationVisible | undefined) =>
    setContext(VISIBILITY_KEY, get);

export const getTreeAnnotationVisibility = (): (() => IsAnnotationVisible | undefined) =>
    getContext<(() => IsAnnotationVisible | undefined) | undefined>(VISIBILITY_KEY) ??
    (() => undefined);
