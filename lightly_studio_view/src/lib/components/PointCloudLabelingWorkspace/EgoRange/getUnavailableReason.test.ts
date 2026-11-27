import { describe, expect, it } from 'vitest';
import { getUnavailableReason } from './getUnavailableReason';

const available = {
    enabled: true,
    egoFrame: 'CABIN',
    referenceFrameId: 'map',
    isShowingSensorFrames: false,
    position: [1, 2, 0] as const
};

describe('getUnavailableReason', () => {
    it('returns null while the ego range is off', () => {
        expect(getUnavailableReason({ ...available, enabled: false, position: null })).toBeNull();
    });

    it('asks for an ego frame when none is picked', () => {
        expect(getUnavailableReason({ ...available, egoFrame: null })).toBe(
            'Pick the ego frame in the scene settings.'
        );
    });

    it('explains that point clouds are in their sensor frames', () => {
        expect(getUnavailableReason({ ...available, isShowingSensorFrames: true })).toBe(
            'Ego range unavailable: point clouds are shown in their sensor frames.'
        );
    });

    it('prefers the sensor frame reason over a missing position', () => {
        expect(
            getUnavailableReason({ ...available, isShowingSensorFrames: true, position: null })
        ).toBe('Ego range unavailable: point clouds are shown in their sensor frames.');
    });

    it('names the reference frame when the ego position is unknown', () => {
        expect(getUnavailableReason({ ...available, position: null })).toBe(
            'Ego position unavailable in frame map.'
        );
    });

    it('returns null while the ego position loads', () => {
        expect(getUnavailableReason({ ...available, position: undefined })).toBeNull();
    });

    it('returns null when the ego position is known', () => {
        expect(getUnavailableReason(available)).toBeNull();
    });
});
