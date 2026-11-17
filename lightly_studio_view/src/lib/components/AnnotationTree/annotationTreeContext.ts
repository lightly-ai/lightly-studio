import { getContext, setContext } from 'svelte';
import type { AnnotationsFilter, AnnotationView } from '$lib/api/lightly_studio_local';

const KEY = Symbol('sample-details-follow-tree');

/** Lets image sample details know that they follow the annotation tree of the Images grid. */
export const setSampleDetailsFollowTree = (followsTree: () => boolean) =>
    setContext(KEY, followsTree);

export const getSampleDetailsFollowTree = (): (() => boolean) =>
    getContext<(() => boolean) | undefined>(KEY) ?? (() => false);

const FLAT_TREE_KEY = Symbol('flat-annotation-tree-collection-id');

/**
 * Lets the Annotations page know the images collection whose tree it follows. It is undefined
 * when the parent collection is not an images collection.
 */
export const setFlatAnnotationTreeCollectionId = (getId: () => string | undefined) =>
    setContext(FLAT_TREE_KEY, getId);

export const getFlatAnnotationTreeCollectionId = (): (() => string | undefined) =>
    getContext<(() => string | undefined) | undefined>(FLAT_TREE_KEY) ?? (() => undefined);

type TreeFilter = Pick<AnnotationsFilter, 'annotation_pairs'>;

const FLAT_TREE_FILTER_KEY = Symbol('flat-annotation-tree-filter');

/** Lets annotation details step through the annotations that the flat tree ticks. */
export const setFlatAnnotationTreeFilter = (get: () => TreeFilter | undefined) =>
    setContext(FLAT_TREE_FILTER_KEY, get);

export const getFlatAnnotationTreeFilter = (): (() => TreeFilter | undefined) =>
    getContext<(() => TreeFilter | undefined) | undefined>(FLAT_TREE_FILTER_KEY) ??
    (() => undefined);

type IsAnnotationVisible = (annotation: AnnotationView) => boolean;

const VISIBILITY_KEY = Symbol('annotation-tree-visibility');

/** Lets the tiles of the Annotations grid follow the tree eyes, which are undefined when off. */
export const setTreeAnnotationVisibility = (get: () => IsAnnotationVisible | undefined) =>
    setContext(VISIBILITY_KEY, get);

export const getTreeAnnotationVisibility = (): (() => IsAnnotationVisible | undefined) =>
    getContext<(() => IsAnnotationVisible | undefined) | undefined>(VISIBILITY_KEY) ??
    (() => undefined);
