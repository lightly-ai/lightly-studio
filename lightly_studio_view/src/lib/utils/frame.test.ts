import { describe, it, expect } from 'vitest';
import { findFrame } from './frame';
import type { FrameView } from '$lib/api/lightly_studio_local';

const createFrame = (frame_timestamp_s: number, sample_id: string): FrameView =>
    ({
        frame_number: 0,
        frame_timestamp_s,
        sample_id,
        sample: {} as FrameView['sample']
    }) as FrameView;

describe('findFrame', () => {
    it('returns nulls when frames list is empty', () => {
        const result = findFrame({ frames: [], currentTime: 1 });

        expect(result).toEqual({ frame: null, index: null });
    });

    it('returns first frame when current time precedes earliest timestamp', () => {
        const frames = [createFrame(0.2, 'a'), createFrame(0.4, 'b')];

        const result = findFrame({ frames, currentTime: 0.1 });

        expect(result).toEqual({ frame: frames[0], index: 0 });
    });

    it('returns frame with greatest timestamp not exceeding current time', () => {
        const frames = [createFrame(0, 'a'), createFrame(1, 'b'), createFrame(2, 'c')];

        const result = findFrame({ frames, currentTime: 1.4 });

        expect(result).toEqual({ frame: frames[1], index: 1 });
    });

    it('returns final frame when current time exceeds last timestamp', () => {
        const frames = [createFrame(0, 'a'), createFrame(1, 'b'), createFrame(3, 'c')];

        const result = findFrame({ frames, currentTime: 5 });

        expect(result).toEqual({ frame: frames[2], index: 2 });
    });
});
