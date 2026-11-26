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
    // True from the moment this page calls history.back() until the popstate lands.
    let isHistoryBackPending = false;
    // Whether the current history entry is one that this page pushed to open a camera.
    let isOnCameraEntry = page.state.cameraEntry ?? false;

    const syncFromUrl = () => {
        ({ tick: currentTick, camera: openCamera } = getUrlState(page.url.hash));
    };

    // `state` defaults to the state of the current entry, so replace writes keep its marker.
    const writeHash = (historyMode: HistoryMode, state: App.PageState = page.state) => {
        const url = new URL(page.url);
        url.hash = buildSequenceHash({ tick: currentTick, camera: openCamera });
        void goto(url, {
            replaceState: historyMode === 'replace',
            noScroll: true,
            keepFocus: true,
            state
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
        const wasClosingCamera = isHistoryBackPending;
        const leftCameraEntry = isOnCameraEntry;
        // A newer navigation can supersede the popstate of history.back(), so any landed
        // navigation ends the wait.
        isHistoryBackPending = false;
        isOnCameraEntry = page.state.cameraEntry ?? false;
        if (type !== 'popstate') return;
        const crossesCameraEntry = wasClosingCamera || leftCameraEntry || isOnCameraEntry;
        if (from?.url.pathname !== to?.url.pathname || !crossesCameraEntry) {
            syncFromUrl();
            return;
        }
        // Moving on or off a camera entry only opens or closes the camera. The entry holds the
        // tick from when the camera opened, so keep the live one and stamp it onto the entry.
        openCamera = getCameraFromHash(page.url.hash);
        writeHash('replace');
    });

    const setTick = (tick: number) => {
        currentTick = tick;
        // The pending popstate writes the live tick once it lands.
        if (!isHistoryBackPending) writeHash('replace');
    };

    const setOpenCamera = (camera: string | undefined, historyMode: HistoryMode) => {
        // Only a committed push carries the marker: a tick write that supersedes a pending push
        // copies the state of the entry before it.
        if (camera === undefined && page.state.cameraEntry) {
            // Pop the entry that opened the camera, so back and close leave the same page.
            openCamera = undefined;
            isHistoryBackPending = true;
            history.back();
            return;
        }
        openCamera = camera;
        writeHash(
            historyMode,
            historyMode === 'push' ? { ...page.state, cameraEntry: true } : page.state
        );
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
