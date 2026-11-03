import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import {
    isAnnotationShown,
    setActivePairFilterCollection,
    useAnnotationPairFilter
} from './useAnnotationPairFilter';
import { NO_MATCH_PAIR } from './pairFilter.helpers';

const IMAGES = 'images-collection';
const ANNOTATIONS = 'annotations-collection';
const pair = (source: string, label: string) => ({
    collection_id: source,
    annotation_label_id: `${label}-id`,
    label_name: label
});
const request = ({ collection_id, annotation_label_id }: ReturnType<typeof pair>) => ({
    collection_id,
    annotation_label_id
});
const GT_DEER = pair('gt', 'deer');
const GT_RACCOON = pair('gt', 'raccoon');
const MODEL_DEER = pair('model', 'deer');

describe('useAnnotationPairFilter', () => {
    beforeEach(() => {
        for (const id of [IMAGES, ANNOTATIONS]) {
            const filter = useAnnotationPairFilter(id);
            filter.clear();
            filter.setKnownPairs([GT_DEER, GT_RACCOON, MODEL_DEER]);
        }
    });

    it('sends no pair filter while everything is ticked', () => {
        const { pairs, includeUnannotated, isActive } = useAnnotationPairFilter(IMAGES);

        expect(get(pairs)).toEqual([]);
        expect(get(includeUnannotated)).toBe(false);
        expect(get(isActive)).toBe(false);
    });

    it('sends the ticked pairs and the unannotated images once one pair is unticked', () => {
        const { pairs, includeUnannotated, togglePair } = useAnnotationPairFilter(IMAGES);

        togglePair(GT_RACCOON);

        expect(get(pairs)).toEqual([request(GT_DEER), request(MODEL_DEER)]);
        expect(get(includeUnannotated)).toBe(true);
    });

    it('sends every pair without unannotated images when only "No annotations" is unticked', () => {
        const { pairs, includeUnannotated, setUnannotatedTicked } = useAnnotationPairFilter(IMAGES);

        setUnannotatedTicked(false);

        expect(get(pairs)).toHaveLength(3);
        expect(get(includeUnannotated)).toBe(false);
    });

    it('sends a pair that matches nothing when nothing is ticked', () => {
        const filter = useAnnotationPairFilter(IMAGES);

        filter.setUnticked([GT_DEER, GT_RACCOON, MODEL_DEER]);
        filter.setUnannotatedTicked(false);

        expect(get(filter.pairs)).toEqual([NO_MATCH_PAIR]);
    });

    it('keeps a new pair ticked', () => {
        const filter = useAnnotationPairFilter(IMAGES);
        filter.togglePair(GT_RACCOON);

        filter.setKnownPairs([GT_DEER, GT_RACCOON, MODEL_DEER, pair('gt', 'fox')]);

        expect(get(filter.pairs)).toContainEqual(request(pair('gt', 'fox')));
    });

    it('keeps the ticks of each tab apart', () => {
        useAnnotationPairFilter(IMAGES).togglePair(GT_DEER);

        expect(get(useAnnotationPairFilter(ANNOTATIONS).unticked)).toEqual([]);
        expect(get(useAnnotationPairFilter(IMAGES).unticked)).toEqual([GT_DEER]);
    });

    it('drops the unticked pairs of a deleted source', () => {
        const filter = useAnnotationPairFilter(IMAGES);
        filter.setUnticked([GT_DEER, MODEL_DEER]);

        filter.dropSource('model');

        expect(get(filter.unticked)).toEqual([GT_DEER]);
    });

    it('draws only the annotations of ticked pairs in the collection on screen', () => {
        setActivePairFilterCollection(IMAGES);
        useAnnotationPairFilter(IMAGES).togglePair(GT_DEER);

        expect(get(isAnnotationShown)('gt', 'deer')).toBe(false);
        expect(get(isAnnotationShown)('model', 'deer')).toBe(true);

        setActivePairFilterCollection(ANNOTATIONS);
        expect(get(isAnnotationShown)('gt', 'deer')).toBe(true);
    });
});
