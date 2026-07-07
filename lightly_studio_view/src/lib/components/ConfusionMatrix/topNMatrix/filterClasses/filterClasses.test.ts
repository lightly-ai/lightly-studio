import { describe, expect, it } from 'vitest';
import { filterClasses } from './filterClasses';

describe('filterClasses', () => {
    const classes = ['bike', 'car', 'person', 'traffic light'];

    it('matches a single term as case-insensitive substring', () => {
        expect(filterClasses(classes, 'CAR')).toEqual(['car']);
        expect(filterClasses(classes, 'i')).toEqual(['bike', 'traffic light']);
    });

    it('OR-combines comma-separated terms', () => {
        expect(filterClasses(classes, 'car, bike')).toEqual(['bike', 'car']);
        expect(filterClasses(classes, 'person,traffic')).toEqual(['person', 'traffic light']);
    });

    it('ignores empty terms and returns all classes for a blank query', () => {
        expect(filterClasses(classes, '')).toEqual(classes);
        expect(filterClasses(classes, ' , ,')).toEqual(classes);
        expect(filterClasses(classes, 'car, ,')).toEqual(['car']);
    });
});
