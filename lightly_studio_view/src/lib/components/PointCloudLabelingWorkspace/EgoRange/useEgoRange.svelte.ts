import { fromStore } from 'svelte/store';
import { useLocalStorage } from '$lib/hooks/useLocalStorage/useLocalStorage';
import type { EgoRange } from './egoRange';
import {
    clampEgoRangeRadius,
    DEFAULT_EGO_RANGE_SETTINGS,
    resolveEgoFrame,
    sanitizeEgoRangeSettings,
    type EgoRangeSettings
} from './egoRangeSettings';
import { getUnavailableReason } from './getUnavailableReason';
import { useEgoPosition } from './useEgoPosition.svelte';
import { resolveEgoPosition } from './resolveEgoPosition';

interface UseEgoRangeInputs {
    datasetId: string;
    sequenceId: string;
    seqNumber: number;
    /** Frame the scene is shown in. */
    referenceFrameId: string;
    /** Frames of the sequence that the scene can be shown in. */
    referenceFrames: readonly string[];
    /** True when some point clouds stay in their sensor frames. */
    isShowingSensorFrames: boolean;
}

/** Owns the ego range preferences and the ego position of the current tick. */
export function useEgoRange(getInputs: () => UseEgoRangeInputs) {
    const store = useLocalStorage<EgoRangeSettings>(
        'lightlyStudio_pointCloudEgoRange',
        DEFAULT_EGO_RANGE_SETTINGS
    );
    store.update(sanitizeEgoRangeSettings);
    const settings = fromStore(store);

    const egoFrame = $derived(
        resolveEgoFrame(
            settings.current.egoFrameByDataset[getInputs().datasetId],
            getInputs().referenceFrames
        )
    );
    const canQuery = $derived(
        settings.current.enabled &&
            egoFrame !== null &&
            Boolean(getInputs().referenceFrameId) &&
            !getInputs().isShowingSensorFrames
    );

    const { query } = useEgoPosition(() => ({
        datasetId: getInputs().datasetId,
        sequenceId: getInputs().sequenceId,
        seqNumber: getInputs().seqNumber,
        referenceFrameId: getInputs().referenceFrameId,
        egoFrameId: egoFrame ?? '',
        enabled: canQuery
    }));

    const position = $derived(
        resolveEgoPosition({ canQuery, isError: query.isError, position: query.data?.position })
    );
    const unavailableReason = $derived(
        getUnavailableReason({
            enabled: settings.current.enabled,
            egoFrame,
            referenceFrameId: getInputs().referenceFrameId,
            isShowingSensorFrames: getInputs().isShowingSensorFrames,
            position
        })
    );
    const range = $derived<EgoRange | null>(
        position && !unavailableReason ? { position, radius: settings.current.radius } : null
    );

    return {
        get enabled() {
            return settings.current.enabled;
        },
        get radius() {
            return settings.current.radius;
        },
        get egoFrame() {
            return egoFrame;
        },
        get egoFrameOptions() {
            return getInputs().referenceFrames;
        },
        get range() {
            return range;
        },
        get unavailableReason() {
            return unavailableReason;
        },
        setEnabled: (enabled: boolean) => store.update((current) => ({ ...current, enabled })),
        setRadius: (radius: number) =>
            store.update((current) => ({ ...current, radius: clampEgoRangeRadius(radius) })),
        setEgoFrame: (frame: string) =>
            store.update((current) => ({
                ...current,
                egoFrameByDataset: {
                    ...current.egoFrameByDataset,
                    [getInputs().datasetId]: frame
                }
            }))
    };
}
