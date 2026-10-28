import { useAnnotationCollectionsFilter } from '$lib/hooks';
import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useAnnotationSourceGroupState } from './useAnnotationSourceGroupState';

describe('useAnnotationSourceGroupState', () => {
    it('drops the stored visibility of a source when its grid filter changes', () => {
        const { setSelectedCollectionIds } = useAnnotationCollectionsFilter();
        const { sourceGroupStates, setSourceGroupState } = useAnnotationSourceGroupState();
        setSelectedCollectionIds(['source-gt', 'source-pred']);
        setSourceGroupState('source-gt', { open: false, hidden: true });
        setSourceGroupState('source-pred', { hidden: true });

        setSelectedCollectionIds(['source-pred']);

        expect(get(sourceGroupStates)).toEqual({
            'source-gt': { open: false },
            'source-pred': { hidden: true }
        });
    });
});
