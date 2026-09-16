import type { CollectionView } from '$lib/api/lightly_studio_local';
import { SampleType } from '$lib/api/lightly_studio_local';
import { getMenuItem } from '$lib/components/NavigationMenu/utils';
import type { NavigationMenuItem } from '$lib/components/NavigationMenu/types';

export interface SidebarNavItem extends NavigationMenuItem {
    /** Row count shown right-aligned, or `undefined` while it is still loading. */
    count: number | undefined;
}

interface BuildSidebarNavItemsParams {
    /** The dataset's root collection, whose children are its sibling views. */
    rootCollection: CollectionView;
    /** Collection currently open, used to mark the active row. */
    currentCollectionId: string | undefined;
    datasetId: string;
    /** Sample count of the root collection. */
    sampleCount: number | undefined;
    /** Annotation count across the currently selected sources. */
    annotationCount: number | undefined;
}

/**
 * Flatten a dataset into the sidebar's nav rows: the root view (Images / Videos) followed by
 * every collection beneath it (Annotations, Frames, Captions, …).
 *
 * The header breadcrumb walked the hierarchy one level at a time; the sidebar shows the whole
 * dataset at once, so nesting is dropped in favour of one row per collection. The walk goes all
 * the way down — a video dataset keeps its frames' captions a level deeper, and those would be
 * unreachable if only direct children were listed.
 */
export function buildSidebarNavItems({
    rootCollection,
    currentCollectionId,
    datasetId,
    sampleCount,
    annotationCount
}: BuildSidebarNavItemsParams): SidebarNavItem[] {
    const collections = flattenCollections(rootCollection);

    return collections.map((collection) => ({
        ...getMenuItem(
            datasetId,
            currentCollectionId,
            collection.collection_id,
            collection.sample_type,
            collection.group_component_name
        ),
        count:
            collection.sample_type === SampleType.ANNOTATION
                ? annotationCount
                : collection.collection_id === rootCollection.collection_id
                  ? sampleCount
                  : undefined
    }));
}

function flattenCollections(collection: CollectionView): CollectionView[] {
    return [collection, ...(collection.children ?? []).flatMap(flattenCollections)];
}
