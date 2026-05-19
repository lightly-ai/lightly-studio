import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { usePlotColorByType } from './usePlotColorByType';

describe('usePlotColorByType', () => {
    beforeEach(() => {
        usePlotColorByType('collection-a').clearSelectedColorByType();
        usePlotColorByType('collection-b').clearSelectedColorByType();
    });

    it('stores metadata as the selected type', () => {
        const colorByType = usePlotColorByType('collection-a');

        colorByType.setSelectedColorByType('metadata');

        expect(get(colorByType.selectedColorByType)).toBe('metadata');
    });

    it('stores annotations and tags per collection', () => {
        const colorByType = usePlotColorByType('collection-a');

        colorByType.setSelectedColorByType('annotation_label');
        expect(get(colorByType.selectedColorByType)).toBe('annotation_label');

        colorByType.setSelectedColorByType('tags');
        expect(get(colorByType.selectedColorByType)).toBe('tags');
    });

    it('keeps collections isolated', () => {
        const colorByTypeA = usePlotColorByType('collection-a');
        const colorByTypeB = usePlotColorByType('collection-b');

        colorByTypeA.setSelectedColorByType('metadata');
        colorByTypeB.setSelectedColorByType('tags');

        expect(get(colorByTypeA.selectedColorByType)).toBe('metadata');
        expect(get(colorByTypeB.selectedColorByType)).toBe('tags');
    });

    it('clears the selected type', () => {
        const colorByType = usePlotColorByType('collection-a');

        colorByType.setSelectedColorByType('annotation_label');
        colorByType.clearSelectedColorByType();

        expect(get(colorByType.selectedColorByType)).toBeNull();
    });
});
