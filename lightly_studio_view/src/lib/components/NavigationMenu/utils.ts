import type { CollectionView } from '$lib/api/lightly_studio_local';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import { Image, WholeWord, Video, Frame, ComponentIcon, LayoutDashboard } from '@lucide/svelte';
import type { BreadcrumbLevel, NavigationMenuItem } from './types';

export function getMenuItem(
    datasetId: string,
    currentCollectionId: string | undefined,
    collectionId: string,
    sampleType: SampleType,
    groupComponentName?: string | null
): NavigationMenuItem {
    const collectionType = sampleType.toLowerCase();
    const isSelected = collectionId === currentCollectionId;
    const elementId = `${collectionType}-${collectionId}`;
    switch (sampleType) {
        case SampleType.IMAGE:
            return {
                title: groupComponentName || 'Images',
                id: elementId,
                href: routeHelpers.toSamples(datasetId, collectionType, collectionId),
                isSelected,
                icon: Image
            };

        case SampleType.VIDEO:
            return {
                title: groupComponentName || 'Videos',
                id: elementId,
                href: routeHelpers.toVideos(datasetId, collectionType, collectionId),
                isSelected,
                icon: Video
            };
        case SampleType.VIDEO_FRAME:
            return {
                title: groupComponentName || 'Frames',
                id: elementId,
                icon: Frame,
                href: routeHelpers.toFrames(datasetId, collectionType, collectionId),
                isSelected
            };
        case SampleType.ANNOTATION:
            return {
                title: groupComponentName || 'Annotations',
                id: elementId,
                icon: ComponentIcon,
                href: routeHelpers.toAnnotations(datasetId, collectionType, collectionId),
                isSelected
            };
        case SampleType.CAPTION:
            return {
                title: groupComponentName || 'Captions',
                id: elementId,
                href: routeHelpers.toCaptions(datasetId, collectionType, collectionId),
                isSelected,
                icon: WholeWord
            };
        case SampleType.GROUP:
            return {
                title: groupComponentName || 'Groups',
                id: elementId,
                href: routeHelpers.toGroups(datasetId, collectionType, collectionId),
                isSelected,
                icon: LayoutDashboard
            };
    }
}

/**
 * Finds the path from root to the collection with the given targetId using DFS,
 * then continues to a leaf by always selecting the first child.
 * Returns an array [root, child, ..., target, ..., leaf] or null if not found.
 */
export function findNavigationPath(
    root: CollectionView,
    targetId: string
): CollectionView[] | null {
    const navigationPath = findPathToTarget(root, targetId);
    if (!navigationPath) return null;

    // Continue from the target to a leaf via first children
    let current = navigationPath[navigationPath.length - 1];
    while (current.children && current.children.length > 0) {
        current = current.children[0];
        navigationPath.push(current);
    }

    return navigationPath;
}

function findPathToTarget(root: CollectionView, targetId: string): CollectionView[] | null {
    if (root.collection_id === targetId) {
        return [root];
    }

    if (!root.children) {
        return null;
    }

    for (const child of root.children) {
        const path = findPathToTarget(child, targetId);
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
    currentCollectionId: string | undefined,
    datasetId: string
): BreadcrumbLevel[] {
    if (!ancestorPath) return [];

    const toMenuItem = (c: CollectionView): NavigationMenuItem =>
        getMenuItem(
            datasetId,
            currentCollectionId,
            c.collection_id,
            c.sample_type,
            c.group_component_name
        );

    return ancestorPath.map((node, index) => {
        const siblings = index === 0 ? [rootCollection] : (ancestorPath[index - 1].children ?? []);

        return {
            selected: toMenuItem(node),
            siblings: siblings.map((sibling) => toMenuItem(sibling))
        };
    });
}
