import { describe, expect, it } from 'vitest';
import { selectVisibleClasses } from './selectVisibleClasses';
import { small3Classes } from '../fixtures';
import type { ClassSetConfig } from '../ClassSetDialog/types';

const baseConfig: ClassSetConfig = {
    mode: 'topN',
    n: 3,
    sortBy: 'most-confused',
    manualClasses: []
};

describe('selectVisibleClasses', () => {
    it('keeps the top-N most-confused classes in matrix order', () => {
        // most-confused ranking is person, car, bike; n=2 keeps person+car,
        // returned in the matrix's original order (bike, car, person).
        expect(selectVisibleClasses(small3Classes, { ...baseConfig, n: 2 })).toEqual([
            'car',
            'person'
        ]);
    });

    it('keeps all real classes when n covers them', () => {
        expect(selectVisibleClasses(small3Classes, { ...baseConfig, n: 10 })).toEqual([
            'bike',
            'car',
            'person'
        ]);
    });

    it('keeps only the manually selected classes in manual mode', () => {
        const config: ClassSetConfig = {
            ...baseConfig,
            mode: 'manual',
            manualClasses: ['person', 'bike']
        };
        expect(selectVisibleClasses(small3Classes, config)).toEqual(['bike', 'person']);
    });

    it('ignores manual selections that are not real classes', () => {
        const config: ClassSetConfig = { ...baseConfig, mode: 'manual', manualClasses: ['ghost'] };
        expect(selectVisibleClasses(small3Classes, config)).toEqual([]);
    });
});
