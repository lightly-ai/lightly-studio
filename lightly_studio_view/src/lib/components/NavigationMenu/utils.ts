import type { CollectionView } from '$lib/api/lightly_studio_local';
import { SampleType } from '$lib/api/lightly_studio_local';
import { APP_ROUTES, routeHelpers } from '$lib/routes';
import { Image, WholeWord, Video, Frame, ComponentIcon, LayoutDashboard } from '@lucide/svelte';
import type { BreadcrumbLevel, NavigationMenuItem } from './types';

export function getMenuItem(
    sampleType: SampleType,
    pageId: string | null,
    datasetId: string,
    collectionType: string,
    collectionId: string
): NavigationMenuItem {
    switch (sampleType) {
        case SampleType.IMAGE:
            return {
                title: 'Images',
                id: `samples-${collectionId}`,
                href: routeHelpers.toSamples(datasetId, collectionType, collectionId),
                isSelected:
                    pageId === APP_ROUTES.samples || pageId === APP_ROUTES.sampleDetails,
                icon: Image
            };

        case SampleType.VIDEO:
            return {
                title: 'Videos',
                id: `videos-${collectionId}`,
                href: routeHelpers.toVideos(datasetId, collectionType, collectionId),
                isSelected: pageId === APP_ROUTES.videos || pageId === APP_ROUTES.videoDetails,
                icon: Video
            };
        case SampleType.VIDEO_FRAME:
            return {
                title: 'Frames',
                id: `frames-${collectionId}`,
                icon: Frame,
                href: routeHelpers.toFrames(datasetId, collectionType, collectionId),
                isSelected: pageId == APP_ROUTES.frames || pageId == APP_ROUTES.framesDetails
            };
        case SampleType.ANNOTATION:
            return {
                title: 'Annotations',
                id: `annotations-${collectionId}`,
                icon: ComponentIcon,
                href: routeHelpers.toAnnotations(datasetId, collectionType, collectionId),
                isSelected:
                    pageId == APP_ROUTES.annotations || pageId == APP_ROUTES.annotationDetails
            };
        case SampleType.CAPTION:
            return {
                title: 'Captions',
                id: `captions-${collectionId}`,
                href: routeHelpers.toCaptions(datasetId, collectionType, collectionId),
                isSelected: pageId === APP_ROUTES.captions,
                icon: WholeWord
            };
        case SampleType.GROUP:
            return {
                title: 'Groups',
                id: 'groups',
                href: routeHelpers.toGroups(datasetId, collectionType, collectionId),
                isSelected: pageId === APP_ROUTES.groups,
                icon: LayoutDashboard
            };
    }
}

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
    toMenuItem: (collection: CollectionView) => NavigationMenuItem
): BreadcrumbLevel[] {
    if (!ancestorPath) return [];

    return ancestorPath.map((node, index) => {
        const siblings = index === 0 ? [rootCollection] : (ancestorPath[index - 1].children ?? []);

        return {
            selected: toMenuItem(node),
            siblings: siblings.map((sibling) => toMenuItem(sibling))
        };
    });
}
