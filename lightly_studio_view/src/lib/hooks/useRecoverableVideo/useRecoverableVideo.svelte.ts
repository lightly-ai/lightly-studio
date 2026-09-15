import { tick } from 'svelte';
import {
    isMediaDirectUrlsEnabled,
    MEDIA_RECOVERY_WATCHDOG_MS,
    withProxyMediaMode
} from '$lib/utils';
import { captureVideoPlayback, restoreVideoPlayback } from './videoRecovery';

interface UseRecoverableVideoParams {
    getSourceUrl: () => string;
    getVideoEl: () => HTMLVideoElement | null;
    getWatchdogMs?: () => number | undefined;
}

export function useRecoverableVideo({
    getSourceUrl,
    getVideoEl,
    getWatchdogMs
}: UseRecoverableVideoParams) {
    let sourceUrl = $state('');
    let terminalError = $state<string | null>(null);
    let appSourceUrl = '';
    let fallbackAttempted = false;
    let recoveryInProgress = false;
    let playbackIntent = false;
    let generation = 0;
    let recoveryController: AbortController | null = null;
    let watchdog: ReturnType<typeof setTimeout> | null = null;

    $effect(() => {
        const nextSourceUrl = getSourceUrl();
        if (nextSourceUrl === appSourceUrl) return;
        generation += 1;
        appSourceUrl = nextSourceUrl;
        sourceUrl = nextSourceUrl;
        terminalError = null;
        fallbackAttempted = false;
        recoveryInProgress = false;
        playbackIntent = false;
        recoveryController?.abort();
        clearWatchdog();

        return () => {
            generation += 1;
            recoveryController?.abort();
            clearWatchdog();
        };
    });

    $effect(() => {
        const video = getVideoEl();
        if (!video) return;

        const handlePlay = () => {
            playbackIntent = true;
            armWatchdog();
        };
        const handlePause = () => {
            if (!recoveryInProgress) playbackIntent = false;
            clearWatchdog();
        };
        const handleEnded = () => {
            playbackIntent = false;
            clearWatchdog();
        };
        const handleSeeking = () => {
            if (!recoveryInProgress) armWatchdog();
        };
        const handleWaiting = () => {
            if (playbackIntent && !recoveryInProgress) armWatchdog();
        };
        const handleLoadStart = () => {
            if ((playbackIntent || video.preload === 'none') && !recoveryInProgress) {
                armWatchdog();
            }
        };
        const handleProgress = () => {
            terminalError = null;
            if (playbackIntent && !recoveryInProgress) armWatchdog();
            else clearWatchdog();
        };
        const handleError = () => void recoverThroughProxy();

        video.addEventListener('play', handlePlay);
        video.addEventListener('pause', handlePause);
        video.addEventListener('ended', handleEnded);
        video.addEventListener('seeking', handleSeeking);
        video.addEventListener('waiting', handleWaiting);
        video.addEventListener('stalled', handleWaiting);
        video.addEventListener('loadstart', handleLoadStart);
        video.addEventListener('playing', handleProgress);
        video.addEventListener('timeupdate', handleProgress);
        video.addEventListener('progress', handleProgress);
        video.addEventListener('loadeddata', handleProgress);
        video.addEventListener('error', handleError);

        return () => {
            video.removeEventListener('play', handlePlay);
            video.removeEventListener('pause', handlePause);
            video.removeEventListener('ended', handleEnded);
            video.removeEventListener('seeking', handleSeeking);
            video.removeEventListener('waiting', handleWaiting);
            video.removeEventListener('stalled', handleWaiting);
            video.removeEventListener('loadstart', handleLoadStart);
            video.removeEventListener('playing', handleProgress);
            video.removeEventListener('timeupdate', handleProgress);
            video.removeEventListener('progress', handleProgress);
            video.removeEventListener('loadeddata', handleProgress);
            video.removeEventListener('error', handleError);
            recoveryController?.abort();
            clearWatchdog();
        };
    });

    function armWatchdog() {
        clearWatchdog();
        const watchdogMs = getWatchdogMs?.() ?? MEDIA_RECOVERY_WATCHDOG_MS;
        watchdog = setTimeout(() => void recoverThroughProxy(), watchdogMs);
    }

    function clearWatchdog() {
        if (watchdog === null) return;
        clearTimeout(watchdog);
        watchdog = null;
    }

    async function recoverThroughProxy() {
        clearWatchdog();
        const video = getVideoEl();
        if (!video || recoveryInProgress) return;
        if (fallbackAttempted) {
            terminalError = getVideoError(video);
            return;
        }

        const recoveryGeneration = generation;
        const snapshot = captureVideoPlayback(video, playbackIntent || !video.paused);
        if (!(await isMediaDirectUrlsEnabled()) || recoveryGeneration !== generation) {
            terminalError = getVideoError(video);
            return;
        }

        fallbackAttempted = true;
        recoveryInProgress = true;
        recoveryController = new AbortController();
        sourceUrl = withProxyMediaMode(appSourceUrl);
        await tick();
        if (recoveryGeneration !== generation || recoveryController.signal.aborted) return;

        video.src = sourceUrl;
        video.load();
        try {
            const resumed = await restoreVideoPlayback(video, snapshot, recoveryController.signal);
            if (!resumed && snapshot.shouldPlay) {
                console.warn('Video proxy recovery restored state but playback did not resume.');
            }
            terminalError = null;
        } catch (error) {
            if (!(error instanceof DOMException && error.name === 'AbortError')) {
                terminalError = getVideoError(video);
            }
        } finally {
            if (recoveryGeneration === generation) recoveryInProgress = false;
        }
    }

    return {
        get sourceUrl() {
            return sourceUrl;
        },
        get terminalError() {
            return terminalError;
        }
    };
}

function getVideoError(video: HTMLVideoElement): string {
    const messages: Record<number, string> = {
        1: 'Video loading was canceled.',
        2: 'Network error while loading the video.',
        3: 'Video decoding failed.',
        4: 'Video source is unavailable or unsupported.'
    };
    return (video.error?.code && messages[video.error.code]) || 'Failed to load video source.';
}
