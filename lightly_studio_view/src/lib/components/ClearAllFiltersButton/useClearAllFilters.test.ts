import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import {
    useAnnotationCollectionsFilter,
    useGlobalStorage,
    useTags,
    useVideoFramesBounds
} from '$lib/hooks';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import { useClearAllFilters } from './useClearAllFilters';

describe('useClearAllFilters', () => {
    const collectionId = 'collection-1';
    let storage: ReturnType<typeof useGlobalStorage>;
    const videoBounds = useVideoBounds();
    const framesBounds = useVideoFramesBounds();
    const sources = useAnnotationCollectionsFilter();
    const fullVideoBounds = {
        width: { min: 0, max: 1920 },
        height: { min: 0, max: 1080 },
        duration_s: { min: 0, max: 60 },
        fps: { min: 24, max: 60 }
    };
    const fullFramesBounds = { frame_number: { min: 0, max: 100 } };

    beforeEach(() => {
        storage = useGlobalStorage();
        storage.clearSelectedAnnotationFilterIds();
        storage.updateMetadataBounds({ score: { min: 0, max: 1 } });
        storage.updateMetadataValues({ score: { min: 0, max: 1 } });
        storage.updateCategoricalMetadataValues({});
        useTags({ collection_id: collectionId }).clearTagsSelected();
        videoBounds.updateVideoBounds(fullVideoBounds);
        videoBounds.updateVideoBoundsValues(fullVideoBounds);
        framesBounds.updateVideoFramesBounds(fullFramesBounds);
        framesBounds.updateVideoFramesBoundsValues(fullFramesBounds);
        sources.setCollectionIdToName({ 'source-1': 'GT', 'source-2': 'Predictions' });
        sources.setSelectedCollectionIds(['source-1', 'source-2']);
    });

    it('reports no active filters by default', () => {
        const { hasActiveFilters } = useClearAllFilters(collectionId);
        expect(get(hasActiveFilters)).toBe(false);
    });

    it('clears tags, labels and metadata filters but keeps the sample selection', () => {
        useTags({ collection_id: collectionId }).setTagSelected('tag-1', true);
        storage.setSelectedAnnotationFilterIds('label-1');
        storage.updateMetadataValues({ score: { min: 0.5, max: 1 } });
        storage.updateCategoricalMetadataValues({ weather: ['sunny'] });
        storage.toggleSampleSelection('sample-1', collectionId);

        const { hasActiveFilters, clearAllFilters } = useClearAllFilters(collectionId);
        expect(get(hasActiveFilters)).toBe(true);

        clearAllFilters();

        expect(get(hasActiveFilters)).toBe(false);
        expect(get(storage.metadataValues)).toEqual({ score: { min: 0, max: 1 } });
        expect(get(storage.getSelectedSampleIds(collectionId)).has('sample-1')).toBe(true);
    });

    it('detects and clears video and frame bounds filters', () => {
        videoBounds.updateVideoBoundsValues({ ...fullVideoBounds, fps: { min: 30, max: 60 } });
        framesBounds.updateVideoFramesBoundsValues({ frame_number: { min: 10, max: 100 } });

        const { hasActiveFilters, clearAllFilters } = useClearAllFilters(collectionId);
        expect(get(hasActiveFilters)).toBe(true);

        clearAllFilters();

        expect(get(hasActiveFilters)).toBe(false);
        expect(get(videoBounds.videoBoundsValues)).toEqual(fullVideoBounds);
        expect(get(framesBounds.videoFramesBoundsValues)).toEqual(fullFramesBounds);
    });

    it('detects and re-checks unchecked annotation sources', () => {
        sources.setSelectedCollectionIds(['source-1']);

        const { hasActiveFilters, clearAllFilters } = useClearAllFilters(collectionId);
        expect(get(hasActiveFilters)).toBe(true);

        clearAllFilters();

        expect(get(hasActiveFilters)).toBe(false);
        expect(get(sources.selectedCollectionIds)).toEqual(['source-1', 'source-2']);
    });
});
