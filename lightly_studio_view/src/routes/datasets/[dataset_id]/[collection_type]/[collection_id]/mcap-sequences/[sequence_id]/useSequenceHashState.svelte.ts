import { untrack } from 'svelte';
import { afterNavigate, goto } from '$app/navigation';
import { navigating, page } from '$app/state';
import type { HistoryMode } from '$lib/components/PointCloudLabelingWorkspace/workspaceOptions';
import { buildSequenceHash, getCameraFromHash, getTickNumberFromHash } from './sequenceHash';

interface UseSequenceHashStateParams {
    getSequenceId: () => string;
}

const getUrlState = (hash: string) => ({
    tick: getTickNumberFromHash(hash),
    camera: getCameraFromHash(hash)
});

/**
 * Owns the tick and the open camera of the sequence page and keeps them in the URL hash.
 *
 * Playback writes the hash every tick, so the hash is always built from this state and never
 * patched from a `page.url` that can be stale.
 */
export function useSequenceHashState({ getSequenceId }: UseSequenceHashStateParams) {
    let currentTick = $state(getTickNumberFromHash(page.url.hash));
    let openCamera = $state(getCameraFromHash(page.url.hash));
    // True while this page session pushed the history entry of the open camera.
    let pushedCameraEntry = false;
    // True from the moment this page calls history.back() until the popstate lands.
    let isHistoryBackPending = false;

    const syncFromUrl = () => {
        ({ tick: currentTick, camera: openCamera } = getUrlState(page.url.hash));
        pushedCameraEntry = false;
    };

    const writeHash = (historyMode: HistoryMode) => {
        const url = new URL(page.url);
        url.hash = buildSequenceHash({ tick: currentTick, camera: openCamera });
        void goto(url, {
            replaceState: historyMode === 'replace',
            noScroll: true,
            keepFocus: true,
            state: page.state
        });
    };

    // Another sequence starts without a hash, so drop the tick and camera of the previous one.
    let syncedSequenceId: string | undefined;
    $effect.pre(() => {
        const sequenceId = getSequenceId();
        const previousSequenceId = syncedSequenceId;
        syncedSequenceId = sequenceId;
        if (previousSequenceId !== undefined && previousSequenceId !== sequenceId) {
            untrack(syncFromUrl);
        }
    });

    // A hash edit in the address bar changes the URL without a navigation.
    $effect(() => {
        const urlHash = buildSequenceHash(getUrlState(page.url.hash));
        untrack(() => {
            // Navigations, including the hash writes of this page, are handled by afterNavigate.
            if (navigating.type !== null || isHistoryBackPending) return;
            const stateHash = buildSequenceHash({ tick: currentTick, camera: openCamera });
            if (urlHash !== stateHash) syncFromUrl();
        });
    });

    afterNavigate(({ type, from, to }) => {
        if (type !== 'popstate') return;
        isHistoryBackPending = false;
        if (from?.url.pathname !== to?.url.pathname) {
            syncFromUrl();
            return;
        }
        // The landed entry holds a stale tick, so keep the live one and stamp it onto the entry.
        openCamera = getCameraFromHash(page.url.hash);
        pushedCameraEntry = false;
        writeHash('replace');
    });

    const setTick = (tick: number) => {
        currentTick = tick;
        // The pending popstate writes the live tick once it lands.
        if (!isHistoryBackPending) writeHash('replace');
    };

    const setOpenCamera = (camera: string | undefined, historyMode: HistoryMode) => {
        if (camera === undefined && pushedCameraEntry) {
            // Pop the entry that opened the camera, so back and close leave the same page.
            openCamera = undefined;
            pushedCameraEntry = false;
            isHistoryBackPending = true;
            history.back();
            return;
        }
        openCamera = camera;
        if (camera === undefined) pushedCameraEntry = false;
        else pushedCameraEntry ||= historyMode === 'push';
        writeHash(historyMode);
    };

    return {
        get tick() {
            return currentTick;
        },
        get openCamera() {
            return openCamera;
        },
        setTick,
        setOpenCamera
    };
}
