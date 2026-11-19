import { describe, expect, it } from 'vitest';
import { togglePickedSampleId } from './pickedSamples';

describe('togglePickedSampleId', () => {
    it('adds a sample that is not picked', () => {
        expect(togglePickedSampleId(['a'], 'b')).toEqual(['a', 'b']);
    });

    it('removes a sample that is picked', () => {
        expect(togglePickedSampleId(['a', 'b'], 'a')).toEqual(['b']);
    });
});
