interface UseVideoPlaybackParams {
    /** The video element being controlled. */
    getVideoEl: () => HTMLVideoElement | null;
    /** The region wrapper used as the fullscreen target. */
    getRegionEl: () => HTMLDivElement | null;
    /** The media URL; playback resets when it changes. */
    getSrc: () => string;
    /** Start time for the current source; `null` waits (e.g. for a deep-link timestamp). */
    getStartTimeS: () => number | null;
    /** Muted state to assume before the element reports its own. */
    initialMuted?: boolean;
}

/**
 * Mirrors a `<video>` element's playback state into reactive fields and exposes
 * intent callbacks for a custom control bar. Listening via native events (rather
 * than owning state) lets the controls compose with handlers on the element.
 */
export function useVideoPlayback({
    getVideoEl,
    getRegionEl,
    getSrc,
    getStartTimeS,
    initialMuted = true
}: UseVideoPlaybackParams) {
    let currentTimeS = $state(0);
    let durationS = $state(0);
    let isPlaying = $state(false);
    let isMuted = $state(initialMuted);
    let isFullscreen = $state(false);

    // Apply the start time when the source (or start time) changes. An explicit
    // start time avoids racing a reset-to-0 against deep-link seeks.
    $effect(() => {
        const el = getVideoEl();
        const src = getSrc();
        const startTimeS = getStartTimeS();
        if (!el || !src || startTimeS === null) return;

        el.pause();
        isPlaying = false;
        currentTimeS = startTimeS;
        durationS = 0;

        const applyStartTime = () => {
            el.currentTime = startTimeS;
            currentTimeS = startTimeS;
            if (Number.isFinite(el.duration)) durationS = el.duration;
        };

        el.addEventListener('loadedmetadata', applyStartTime, { once: true });
        if (el.getAttribute('src') === src && el.readyState >= HTMLMediaElement.HAVE_METADATA) {
            applyStartTime();
        }

        return () => el.removeEventListener('loadedmetadata', applyStartTime);
    });

    $effect(() => {
        const el = getVideoEl();
        if (!el) return;

        const syncTime = () => (currentTimeS = el.currentTime);
        const syncDuration = () => {
            if (Number.isFinite(el.duration)) durationS = el.duration;
        };
        const syncPlaying = () => (isPlaying = !el.paused);
        const syncMuted = () => (isMuted = el.muted);

        syncTime();
        syncDuration();
        syncPlaying();
        syncMuted();

        el.addEventListener('timeupdate', syncTime);
        el.addEventListener('seeked', syncTime);
        el.addEventListener('loadedmetadata', syncDuration);
        el.addEventListener('durationchange', syncDuration);
        el.addEventListener('play', syncPlaying);
        el.addEventListener('pause', syncPlaying);
        el.addEventListener('volumechange', syncMuted);

        return () => {
            el.removeEventListener('timeupdate', syncTime);
            el.removeEventListener('seeked', syncTime);
            el.removeEventListener('loadedmetadata', syncDuration);
            el.removeEventListener('durationchange', syncDuration);
            el.removeEventListener('play', syncPlaying);
            el.removeEventListener('pause', syncPlaying);
            el.removeEventListener('volumechange', syncMuted);
        };
    });

    // Keep the fullscreen flag in sync however it's entered/left.
    $effect(() => {
        if (typeof document === 'undefined') return;
        const syncFullscreen = () => (isFullscreen = document.fullscreenElement === getRegionEl());
        document.addEventListener('fullscreenchange', syncFullscreen);
        return () => document.removeEventListener('fullscreenchange', syncFullscreen);
    });

    function seekTo(timeS: number) {
        const el = getVideoEl();
        if (!el) return;
        el.currentTime = timeS;
        currentTimeS = timeS;
    }

    function togglePlay() {
        const el = getVideoEl();
        if (!el) return;
        if (el.paused) {
            void el.play();
        } else {
            el.pause();
        }
    }

    function toggleMute() {
        const el = getVideoEl();
        if (!el) return;
        el.muted = !el.muted;
    }

    function toggleFullscreen() {
        if (typeof document === 'undefined') return;
        const regionEl = getRegionEl();
        if (document.fullscreenElement === regionEl) {
            void document.exitFullscreen();
        } else {
            void regionEl?.requestFullscreen();
        }
    }

    return {
        get currentTimeS() {
            return currentTimeS;
        },
        get durationS() {
            return durationS;
        },
        get isPlaying() {
            return isPlaying;
        },
        get isMuted() {
            return isMuted;
        },
        get isFullscreen() {
            return isFullscreen;
        },
        seekTo,
        togglePlay,
        toggleMute,
        toggleFullscreen
    };
}
