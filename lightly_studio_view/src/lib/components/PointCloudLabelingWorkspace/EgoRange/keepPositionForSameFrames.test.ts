import { describe, expect, it } from 'vitest';
import { keepPositionForSameFrames } from './keepPositionForSameFrames';

const previous = { position: [12, -3, 0] };
const frames = { referenceFrameId: 'map', egoFrameId: 'CABIN' };

function previousQuery(query: { target_frame_id: string; ego_frame_id: string }) {
    return { queryKey: [{ query }] };
}

describe('keepPositionForSameFrames', () => {
    it('keeps the previous position of another tick in the same frames', () => {
        const query = previousQuery({ target_frame_id: 'map', ego_frame_id: 'CABIN' });

        expect(keepPositionForSameFrames(previous, query, frames)).toBe(previous);
    });

    it('drops the previous position after the reference frame changes', () => {
        const query = previousQuery({ target_frame_id: 'CABIN', ego_frame_id: 'CABIN' });

        expect(keepPositionForSameFrames(previous, query, frames)).toBeUndefined();
    });

    it('drops the previous position after the ego frame changes', () => {
        const query = previousQuery({ target_frame_id: 'map', ego_frame_id: 'base_link' });

        expect(keepPositionForSameFrames(previous, query, frames)).toBeUndefined();
    });

    it('returns undefined without a previous query', () => {
        expect(keepPositionForSameFrames(undefined, undefined, frames)).toBeUndefined();
    });
});
