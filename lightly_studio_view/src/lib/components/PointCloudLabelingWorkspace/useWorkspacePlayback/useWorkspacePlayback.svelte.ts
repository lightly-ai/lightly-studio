import { fromStore } from 'svelte/store';
import { useMcapTickPrefetchScheduler } from '$lib/hooks';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { getMcapTickPrefetchRange } from '$lib/hooks/useMcapTickDetailsPrefetch/getMcapTickPrefetchRange';
import { usePointCloudTickNavigation } from '../usePointCloudTickNavigation.svelte';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';

/** Manages buffered playback and seek interactions for one workspace. */
export function useWorkspacePlayback(
    getWorkspace: () => PointCloudWorkspaceContext,
    getOptions: () => WorkspaceOptions,
    getAccumulationRadius: () => number = () => 0
) {
    const bufferEntireSequence = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudBufferEntireSequence',
        false
    );
    const buffering = fromStore(bufferEntireSequence);
    let seekWasPlaying = false;
    let bufferingSeekVersion = $state(0);
    let selectedBufferingTick = $state<number | undefined>();
    const tickPrefetch = useMcapTickPrefetchScheduler({
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        getDisplayFrameId: () => getWorkspace().referenceFrameId,
        getTicks: () => getWorkspace().ticks,
        // Keep one buffer while playback advances. A new sequence gets a new buffer.
        // Changing the mode creates a new session, which cancels the old queue. This is important
        // when turning off whole-sequence buffering: its remaining chunks must not continue loading.
        getRequestId: () =>
            `${getOptions().datasetId}/${getOptions().sequenceId}/playback/${getWorkspace().referenceFrameId || 'sensor'}/${buffering.current ? `entire/${selectedBufferingTick ?? getWorkspace().currentTick}` : `window/${bufferingSeekVersion}`}`,
        getRanges: () => {
            const activeTick = selectedBufferingTick ?? getWorkspace().currentTick;
            const activeIndex = getWorkspace().ticks.findIndex(
                (tick) => tick.seq_number === activeTick
            );

            if (buffering.current) {
                return [
                    {
                        startIndex: Math.max(0, activeIndex - getAccumulationRadius()),
                        endIndex: getWorkspace().ticks.length - 1
                    }
                ];
            }

            return getMcapTickPrefetchRange({
                activeIndex,
                tickCount: getWorkspace().ticks.length,
                prefetchTickCount: getOptions().prefetchTickCount ?? 50,
                accumulationRadius: getAccumulationRadius()
            });
        }
    });
    const isTickBuffered = (index: number) => {
        const radius = getAccumulationRadius();
        const start = Math.max(0, index - radius);
        const end = Math.min(getWorkspace().ticks.length - 1, index + radius);
        for (let tick = start; tick <= end; tick++) {
            if (
                !tickPrefetch.bufferedRanges.some(
                    ({ startIndex, endIndex }) => tick >= startIndex && tick <= endIndex
                )
            )
                return false;
        }
        return true;
    };

    const { goToPreviousFrame, goToNextFrame, goToFrame, togglePlayback } =
        usePointCloudTickNavigation({
            getWorkspace,
            getTickNumber: () => getOptions().tickNumber ?? 1,
            getOnTickChange: () => getOptions().onTickChange ?? (() => undefined),
            getIsTickBuffered: isTickBuffered
        });
    const handleSeekStart = () => {
        seekWasPlaying = getWorkspace().isPlaying;
        if (seekWasPlaying) getWorkspace().togglePlayback();
    };
    const handleSeekEnd = () => {
        if (seekWasPlaying && !getWorkspace().isPlaying) getWorkspace().togglePlayback();
        seekWasPlaying = false;
    };
    const handleSelectTick = (seqNumber: number) => {
        selectedBufferingTick = seqNumber;
        bufferingSeekVersion += 1;
        goToFrame(seqNumber);
    };
    const handleWindowKeydown = (event: KeyboardEvent) => {
        if (event.code !== 'Space' || event.repeat) return;
        const target = event.target;
        const isTextEntry =
            target instanceof Element &&
            ((target instanceof HTMLElement && target.isContentEditable) ||
                target.closest('input, select, textarea'));
        if (isTextEntry) return;
        if (target instanceof Element && target.closest('[role="dialog"]')) {
            event.preventDefault();
            togglePlayback();
            return;
        }
        if (
            target instanceof Element &&
            ((target instanceof HTMLElement && target.isContentEditable) ||
                target.closest(
                    'button, a, input, select, textarea, [role="button"], [role="option"], [role="menuitem"]'
                ))
        ) {
            return;
        }
        event.preventDefault();
        togglePlayback();
    };

    return {
        get bufferedRanges() {
            return tickPrefetch.bufferedRanges;
        },
        get bufferEntireSequence() {
            return buffering.current;
        },
        setBufferEntireSequence: bufferEntireSequence.set,
        goToPreviousFrame,
        goToNextFrame,
        togglePlayback,
        handleSelectTick,
        handleSeekStart,
        handleSeekEnd,
        handleWindowKeydown
    };
}
