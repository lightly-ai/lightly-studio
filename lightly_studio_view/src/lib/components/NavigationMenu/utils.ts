import type { CollectionView } from '$lib/api/lightly_studio_local';

/**
 * Finds the path from root to the collection with the given targetId.
 * Returns an array of ancestors [root, child, ..., target] or null if not found.
 */
export function findAncestorPath(root: CollectionView, targetId: string): CollectionView[] | null {
    if (root.collection_id === targetId) {
        return [root];
    }

    if (!root.children) {
        return null;
    }

    for (const child of root.children) {
        const path = findAncestorPath(child, targetId);
        if (path) {
            return [root, ...path];
        }
    }

    return null;
}
