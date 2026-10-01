import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import UseVideoPlaybackHarness from './UseVideoPlaybackHarness.svelte';
import type { useVideoPlayback } from './useVideoPlayback.svelte';

type Playback = ReturnType<typeof useVideoPlayback>;

/** Give a jsdom media element the properties the hook reads. */
function stubMediaProps(
    el: HTMLVideoElement,
    props: { paused?: boolean; muted?: boolean; duration?: number }
) {
    for (const [key, value] of Object.entries(props)) {
        Object.defineProperty(el, key, { value, configurable: true, writable: true });
    }
    el.play = vi.fn().mockResolvedValue(undefined);
    el.pause = vi.fn();
}

interface RenderOptions {
    startTimeS?: number | null;
    src?: string;
    regionEl?: HTMLDivElement | null;
    initialMuted?: boolean;
}

describe('useVideoPlayback', () => {
    let videoEl: HTMLVideoElement;

    beforeEach(() => {
        videoEl = document.createElement('video');
        stubMediaProps(videoEl, { paused: true, muted: false });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    const renderHook = (options: RenderOptions = {}): Playback => {
        let result: Playback | undefined;
        render(UseVideoPlaybackHarness, {
            videoEl,
            regionEl: options.regionEl ?? null,
            src: options.src ?? 'video.mp4',
            // Default to null so the start-time effect stays inert unless a test opts in.
            startTimeS: options.startTimeS ?? null,
            initialMuted: options.initialMuted,
            onReady: (hookResult) => {
                result = hookResult;
            }
        });
        flushSync();

        if (!result) {
            throw new Error('useVideoPlayback harness did not initialize');
        }
        return result;
    };

    it('mirrors play and pause events', () => {
        const playback = renderHook();
        expect(playback.isPlaying).toBe(false);

        // The hook reads `el.paused`, mirroring whatever the element reports.
        Object.defineProperty(videoEl, 'paused', { value: false, configurable: true });
        flushSync(() => videoEl.dispatchEvent(new Event('play')));
        expect(playback.isPlaying).toBe(true);

        Object.defineProperty(videoEl, 'paused', { value: true, configurable: true });
        flushSync(() => videoEl.dispatchEvent(new Event('pause')));
        expect(playback.isPlaying).toBe(false);
    });

    it('mirrors the current time on timeupdate and seeked', () => {
        const playback = renderHook();

        videoEl.currentTime = 5;
        flushSync(() => videoEl.dispatchEvent(new Event('timeupdate')));
        expect(playback.currentTimeS).toBe(5);

        videoEl.currentTime = 8;
        flushSync(() => videoEl.dispatchEvent(new Event('seeked')));
        expect(playback.currentTimeS).toBe(8);
    });

    it('mirrors a finite duration and ignores a non-finite one', () => {
        const playback = renderHook();
        expect(playback.durationS).toBe(0);

        Object.defineProperty(videoEl, 'duration', { value: 20, configurable: true });
        flushSync(() => videoEl.dispatchEvent(new Event('durationchange')));
        expect(playback.durationS).toBe(20);

        Object.defineProperty(videoEl, 'duration', { value: NaN, configurable: true });
        flushSync(() => videoEl.dispatchEvent(new Event('durationchange')));
        // Keeps the last known duration rather than resetting to a bogus value.
        expect(playback.durationS).toBe(20);
    });

    it('mirrors the muted state on volumechange', () => {
        const playback = renderHook();
        expect(playback.isMuted).toBe(false);

        videoEl.muted = true;
        flushSync(() => videoEl.dispatchEvent(new Event('volumechange')));
        expect(playback.isMuted).toBe(true);
    });

    it('seekTo sets the element time and mirrors it immediately', () => {
        const playback = renderHook();
        flushSync(() => playback.seekTo(7));
        expect(videoEl.currentTime).toBe(7);
        expect(playback.currentTimeS).toBe(7);
    });

    it('togglePlay plays when paused and pauses when playing', () => {
        const playback = renderHook();

        playback.togglePlay();
        expect(videoEl.play).toHaveBeenCalledOnce();

        Object.defineProperty(videoEl, 'paused', { value: false, configurable: true });
        playback.togglePlay();
        expect(videoEl.pause).toHaveBeenCalledOnce();
    });

    it('toggleMute flips the element muted flag', () => {
        const playback = renderHook();

        playback.toggleMute();
        expect(videoEl.muted).toBe(true);

        playback.toggleMute();
        expect(videoEl.muted).toBe(false);
    });

    it('applies the start time once metadata is available', () => {
        const playback = renderHook({ startTimeS: 12 });

        Object.defineProperty(videoEl, 'duration', { value: 30, configurable: true });
        flushSync(() => videoEl.dispatchEvent(new Event('loadedmetadata')));

        expect(videoEl.currentTime).toBe(12);
        expect(playback.currentTimeS).toBe(12);
        expect(playback.durationS).toBe(30);
    });

    it('toggleFullscreen requests fullscreen on the region element', () => {
        const regionEl = document.createElement('div');
        const requestFullscreen = vi.fn().mockResolvedValue(undefined);
        regionEl.requestFullscreen = requestFullscreen;

        const playback = renderHook({ regionEl });
        playback.toggleFullscreen();

        expect(requestFullscreen).toHaveBeenCalledOnce();
    });
});
