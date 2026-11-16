import { describe, expect, it } from 'vitest';
import { searchAnnotationClasses } from './AnnotationClassesTab.helpers';

const classes = [
    { annotation_label_name: 'cat' },
    { annotation_label_name: 'bear' },
    { annotation_label_name: 'Beard' }
];
const names = (items: { annotation_label_name: string }[]) =>
    items.map((c) => c.annotation_label_name);

describe('searchAnnotationClasses', () => {
    it('sorts by name and filters case-insensitively', () => {
        const result = searchAnnotationClasses(classes, 'BEA');

        expect(names(result.sortedClasses)).toEqual(['bear', 'Beard', 'cat']);
        expect(names(result.visibleClasses)).toEqual(['bear', 'Beard']);
        expect(result.canAdd).toBe(true);
        expect(result.canAddWithEnter).toBe(false);
    });

    it('does not allow adding a name that exists in another case', () => {
        const result = searchAnnotationClasses(classes, 'Bear');

        expect(result.exactMatch?.annotation_label_name).toBe('bear');
        expect(result.canAdd).toBe(false);
    });

    it('allows adding with Enter when nothing matches', () => {
        const result = searchAnnotationClasses(classes, 'dog');

        expect(result.visibleClasses).toEqual([]);
        expect(result.canAddWithEnter).toBe(true);
    });

    it('does not allow adding before the classes load', () => {
        const result = searchAnnotationClasses(undefined, 'dog');

        expect(result.visibleClasses).toEqual([]);
        expect(result.canAdd).toBe(false);
        expect(result.canAddWithEnter).toBe(false);
    });

    it('does not allow adding an empty name', () => {
        const result = searchAnnotationClasses(classes, '');

        expect(result.visibleClasses).toHaveLength(3);
        expect(result.canAdd).toBe(false);
    });
});
