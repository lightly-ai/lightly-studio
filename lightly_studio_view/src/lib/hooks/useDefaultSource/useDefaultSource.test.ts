import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { useDefaultSource } from './useDefaultSource';

const STORAGE_KEY = 'lightlyStudio_default_annotation_source';

describe('useDefaultSource', () => {
    it('stores the default in local storage', () => {
        const { setDefaultSource } = useDefaultSource();

        setDefaultSource('col-1', 'labels');

        expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')).toEqual({
            'col-1': 'labels'
        });
    });

    it('replaces the default of a collection', () => {
        const { defaultSources, setDefaultSource } = useDefaultSource();
        setDefaultSource('col-1', 'labels');

        setDefaultSource('col-1', 'predictions');

        expect(get(defaultSources)['col-1']).toBe('predictions');
    });

    it('removes the default with null', () => {
        const { defaultSources, setDefaultSource } = useDefaultSource();
        setDefaultSource('col-1', 'labels');

        setDefaultSource('col-1', null);

        expect(get(defaultSources)).not.toHaveProperty('col-1');
    });

    it('follows a rename of the default', () => {
        const { defaultSources, setDefaultSource, renameDefaultSource } = useDefaultSource();
        setDefaultSource('col-1', 'labels');

        renameDefaultSource('col-1', 'labels', 'gt');

        expect(get(defaultSources)['col-1']).toBe('gt');
    });

    it('ignores a rename of another source', () => {
        const { defaultSources, setDefaultSource, renameDefaultSource } = useDefaultSource();
        setDefaultSource('col-1', 'predictions');

        renameDefaultSource('col-1', 'labels', 'gt');

        expect(get(defaultSources)['col-1']).toBe('predictions');
    });
});
