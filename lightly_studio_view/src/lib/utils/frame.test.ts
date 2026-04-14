import { describe, it, expect } from 'vitest';
import { findFrame, getFrameWindowTarget, selectPlaybackFrame } from './frame';
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

describe('selectPlaybackFrame', () => {
    it('returns timestamps and invariant metadata for exact hits', () => {
        const frames = [createFrame(0, 'a'), createFrame(0.5, 'b')];

        const result = selectPlaybackFrame({
            frames,
            sourceTime: 0
        });

        expect(result.frame).toBe(frames[0]);
        expect(result.selectedTimestamp).toBe(0);
        expect(result.nextTimestamp).toBe(0.5);
        expect(result.windowStartTimestamp).toBe(0);
        expect(result.windowEndTimestamp).toBe(0.5);
        expect(result.selectorInvariantHolds).toBe(true);
    });

    it('uses timestamp ordering for irregular frame spacing', () => {
        const frames = [createFrame(0, 'a'), createFrame(0.2, 'b'), createFrame(0.9, 'c')];

        const result = selectPlaybackFrame({
            frames,
            sourceTime: 0.4
        });

        expect(result.frame).toBe(frames[1]);
        expect(result.index).toBe(1);
        expect(result.selectorInvariantHolds).toBe(true);
    });

    it('reports invariant failure before the first timestamp window opens', () => {
        const frames = [createFrame(0.2, 'a'), createFrame(0.4, 'b')];

        const result = selectPlaybackFrame({
            frames,
            sourceTime: 0.1
        });

        expect(result.frame).toBe(frames[0]);
        expect(result.selectorInvariantHolds).toBe(false);
    });

    it('can switch at frame midpoints when requested', () => {
        const frames = [createFrame(0.5, 'a'), createFrame(0.6, 'b'), createFrame(0.7, 'c')];

        const result = selectPlaybackFrame({
            frames,
            sourceTime: 0.59,
            strategy: 'midpoint'
        });

        expect(result.frame).toBe(frames[1]);
        expect(result.strategy).toBe('midpoint');
        expect(result.windowStartTimestamp).toBe(0.55);
        expect(result.windowEndTimestamp).toBeCloseTo(0.65);
        expect(result.selectorInvariantHolds).toBe(true);
    });

    it('uses the nearest timestamp for midpoint selection', () => {
        const frames = [createFrame(1.5, 'a'), createFrame(1.6, 'b')];

        const result = selectPlaybackFrame({
            frames,
            sourceTime: 1.592,
            strategy: 'midpoint'
        });

        expect(result.frame).toBe(frames[1]);
        expect(result.windowStartTimestamp).toBe(1.55);
        expect(result.windowEndTimestamp).toBeNull();
    });
});

describe('getFrameWindowTarget', () => {
    it('uses the current-to-next interval midpoint for paused seeking', () => {
        const frames = [createFrame(0.9, 'a'), createFrame(1.0, 'b'), createFrame(1.1, 'c')];

        const result = getFrameWindowTarget({
            frames,
            frameIndex: 1,
            videoDuration: 2
        });

        expect(result).toEqual({
            frame: frames[1],
            index: 1,
            selectedTimestamp: 1.0,
            windowStartTimestamp: 1.0,
            windowEndTimestamp: 1.1,
            seekTargetTime: 1.05
        });
    });

    it('uses the next frame boundary for the first frame', () => {
        const frames = [createFrame(0.2, 'a'), createFrame(0.4, 'b')];

        const result = getFrameWindowTarget({
            frames,
            frameIndex: 0,
            videoDuration: 2
        });

        expect(result?.windowStartTimestamp).toBe(0.2);
        expect(result?.windowEndTimestamp).toBe(0.4);
        expect(result?.seekTargetTime).toBeCloseTo(0.3);
    });

    it('uses video duration as the end boundary for the last frame', () => {
        const frames = [createFrame(1.8, 'a'), createFrame(1.9, 'b')];

        const result = getFrameWindowTarget({
            frames,
            frameIndex: 1,
            videoDuration: 2
        });

        expect(result?.windowStartTimestamp).toBe(1.9);
        expect(result?.windowEndTimestamp).toBe(2);
        expect(result?.seekTargetTime).toBeCloseTo(1.95);
    });

    it('falls back to a small synthetic tail when duration is unavailable', () => {
        const frames = [createFrame(0, 'a'), createFrame(0.5, 'b')];

        const result = getFrameWindowTarget({
            frames,
            frameIndex: 1
        });

        expect(result?.windowStartTimestamp).toBe(0.5);
        expect(result?.windowEndTimestamp).toBeGreaterThan(0.5);
        expect(result?.seekTargetTime).toBeGreaterThan(0.5);
    });
});
