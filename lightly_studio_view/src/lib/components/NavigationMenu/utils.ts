import type { CollectionView } from '$lib/api/lightly_studio_local';
import type { BreadcrumbLevel, NavigationMenuItem } from './types';

/**
 * Finds the path from root to the collection with the given targetId using DFS.
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

/**
 * Builds breadcrumb levels from an ancestor path.
 * Each level contains the selected node's menu item and all sibling menu items at that depth.
 */
export function buildBreadcrumbLevels(
    ancestorPath: CollectionView[] | null,
    rootCollection: CollectionView,
    toMenuItem: (collection: CollectionView) => NavigationMenuItem | undefined
): BreadcrumbLevel[] {
    if (!ancestorPath) return [];

    return ancestorPath.map((node, index) => {
        const siblings =
            index === 0 ? [rootCollection] : (ancestorPath[index - 1].children ?? []);

        return {
            selected: toMenuItem(node)!,
            siblings: siblings
                .map((sibling) => toMenuItem(sibling))
                .filter((item): item is NavigationMenuItem => !!item)
        };
    });
}
