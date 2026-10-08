import { describe, expect, it } from 'vitest';
import { parseTargets } from './AutoLabelDialog.helpers';

describe('parseTargets', () => {
    it('splits on commas and newlines, trims, and removes empty and duplicate prompts', () => {
        expect(parseTargets(' person, car\nbicycle,,\n car ')).toEqual([
            'person',
            'car',
            'bicycle'
        ]);
    });

    it('returns no prompts for blank text', () => {
        expect(parseTargets('  \n ')).toEqual([]);
    });
});
