import { get } from 'svelte/store';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';

export function useStrategyOptions(getCollectionId: () => string) {
    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const annotationCollectionsQuery = useAnnotationCollections({
        collectionId: getCollectionId()
    });
    const { metadataInfo } = useMetadataFilters(getCollectionId());

    let metadataInfoValue = $state<MetadataInfoView[]>(get(metadataInfo));
    $effect(() => metadataInfo.subscribe((v) => (metadataInfoValue = v)));

    const metadataFieldNames = $derived(
        metadataInfoValue
            .filter((i) => i.type === 'integer' || i.type === 'float')
            .map((i) => i.name)
    );
    const hasMetadataFields = $derived(metadataFieldNames.length > 0);
    const annotationLabels = $derived(
        (annotationLabelsQuery.data ?? []).map((l) => l.annotation_label_name)
    );
    const hasAnnotationLabels = $derived(annotationLabels.length > 0);
    const annotationSourceOptions = $derived(
        (annotationCollectionsQuery.data ?? []).map((c) => ({ id: c.collection_id, name: c.name }))
    );

    return {
        get metadataFieldNames() {
            return metadataFieldNames;
        },
        get hasMetadataFields() {
            return hasMetadataFields;
        },
        get annotationLabels() {
            return annotationLabels;
        },
        get hasAnnotationLabels() {
            return hasAnnotationLabels;
        },
        get annotationSourceOptions() {
            return annotationSourceOptions;
        }
    };
}
