import type { Component } from 'svelte';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import {
    Image,
    WholeWord,
    Video,
    Frame,
    ComponentIcon,
    LayoutDashboard,
    Box
} from '@lucide/svelte';
import type { BreadcrumbLevel, NavigationMenuItem } from './types';

interface GetMenuItemParams {
    datasetId: string;
    currentCollectionId: string | undefined;
    collectionId: string;
    sampleType: SampleType;
    groupComponentName?: string | null;
    rootSampleType?: SampleType;
}

type SampleTypeConfig = {
    icon: Component;
    toHref: (datasetId: string, collectionType: string, collectionId: string) => string;
    title: (groupComponentName?: string | null) => string;
    isHidden?: (rootSampleType?: SampleType) => boolean;
};

const SAMPLE_TYPE_CONFIGS: Partial<Record<SampleType, SampleTypeConfig>> = {
    [SampleType.IMAGE]: {
        icon: Image,
        toHref: (d, t, c) => routeHelpers.toImages(d, t, c),
        title: (name) => name || 'Images'
    },
    [SampleType.VIDEO]: {
        icon: Video,
        toHref: (d, t, c) => routeHelpers.toVideos(d, t, c),
        title: (name) => name || 'Videos'
    },
    [SampleType.VIDEO_FRAME]: {
        icon: Frame,
        toHref: (d, t, c) => routeHelpers.toFrames(d, t, c),
        title: (name) => name || 'Frames'
    },
    [SampleType.ANNOTATION]: {
        icon: ComponentIcon,
        toHref: (d, t, c) => routeHelpers.toAnnotations(d, t, c),
        title: (name) => (name ? `Annotations: ${name}` : 'Annotations')
    },
    [SampleType.CAPTION]: {
        icon: WholeWord,
        toHref: (d, t, c) => routeHelpers.toCaptions(d, t, c),
        title: (name) => name || 'Captions'
    },
    [SampleType.GROUP]: {
        icon: LayoutDashboard,
        toHref: (d, t, c) => routeHelpers.toGroups(d, t, c),
        title: (name) => name || 'Groups',
        isHidden: (rootSampleType) => rootSampleType === SampleType.SEQUENCE
    },
    [SampleType.SEQUENCE]: {
        icon: Box,
        toHref: (d, t, c) => routeHelpers.toPointClouds(d, t, c),
        title: (name) => name || 'Point clouds'
    }
    // MCAP intentionally absent — no dedicated view
};

/**
 * Builds the nav menu item for a collection, or null if the sample type has no
 * dedicated view to navigate to (e.g. MCAP, which has no view yet).
 */
export function getMenuItem({
    datasetId,
    currentCollectionId,
    collectionId,
    sampleType,
    groupComponentName,
    rootSampleType
}: GetMenuItemParams): NavigationMenuItem | null {
    const config = SAMPLE_TYPE_CONFIGS[sampleType];
    if (!config || config.isHidden?.(rootSampleType)) return null;

    const collectionType = sampleType.toLowerCase();
    return {
        title: config.title(groupComponentName),
        id: `${collectionType}-${collectionId}`,
        href: config.toHref(datasetId, collectionType, collectionId),
        isSelected: collectionId === currentCollectionId,
        icon: config.icon
    };
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

    const hasSeveralAnnotationCollections = rootCollection.children
        ? rootCollection.children.filter((c) => c.sample_type === SampleType.ANNOTATION).length > 1
        : false;
    const toMenuItem = (c: CollectionView): NavigationMenuItem | null =>
        getMenuItem({
            datasetId,
            currentCollectionId,
            collectionId: c.collection_id,
            sampleType: c.sample_type,
            // For annotation collections, show the collection name to distinguish them if there are several; otherwise, use the group component name or a generic title.
            groupComponentName:
                c.sample_type === SampleType.ANNOTATION && hasSeveralAnnotationCollections
                    ? c.name
                    : c.group_component_definition?.group_component_name,
            rootSampleType: rootCollection.sample_type
        });
    const isNavigationMenuItem = (item: NavigationMenuItem | null): item is NavigationMenuItem =>
        item !== null;

    return ancestorPath
        .map((node, index) => {
            const selected = toMenuItem(node);
            if (!selected) return null;

            const siblings =
                index === 0 ? [rootCollection] : (ancestorPath[index - 1].children ?? []);

            return {
                selected,
                siblings: siblings
                    .map((sibling) => toMenuItem(sibling))
                    .filter(isNavigationMenuItem)
            };
        })
        .filter((level): level is BreadcrumbLevel => level !== null);
}
