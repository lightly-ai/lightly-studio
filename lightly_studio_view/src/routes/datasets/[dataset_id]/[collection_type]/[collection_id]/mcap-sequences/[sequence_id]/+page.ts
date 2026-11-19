import { SampleType } from '$lib/api/lightly_studio_local';
import { fetchCollectionHierarchy } from '$lib/utils';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url, parent }) => {
    // Point-cloud data is resolved by the dataset entity id, which the collection carries directly.
    // The URL's dataset slot is a collection id, so derive the dataset id from the loaded collection.
    const { collection, collectionHierarchy } = await parent();
    // Reached from a group component, the loaded collection is the GROUP, but its MCAP sequences
    // live in the parent SEQUENCE collection. The breadcrumb points at that sequence collection so
    // the point-cloud grid it links to is scoped to the collection that holds the sequences.
    const breadcrumbCollection =
        collection.sample_type === SampleType.GROUP && collection.parent_collection_id
            ? (collectionHierarchy.find(
                  (candidate) => candidate.collection_id === collection.parent_collection_id
              ) ?? collection)
            : collection;
    // The collection layout skips loading the hierarchy when this is the root collection.
    // Point-cloud annotation sources are children of the MCAP GROUP collection.
    const hierarchy =
        collection.sample_type === SampleType.GROUP || collectionHierarchy.length > 0
            ? collectionHierarchy
            : await fetchCollectionHierarchy(collection.collection_id);
    const annotationSourceCollection =
        collection.sample_type === SampleType.GROUP
            ? collection
            : hierarchy.find((candidate) => candidate.sample_type === SampleType.GROUP);
    return {
        datasetId: collection.dataset_id,
        annotationSourceCollectionId: annotationSourceCollection?.collection_id,
        collectionName: breadcrumbCollection.name,
        collectionType: breadcrumbCollection.sample_type,
        collectionId: breadcrumbCollection.collection_id,
        sequenceId: params.sequence_id,
        groupId: url.searchParams.get('group_id') ?? undefined
    };
};
