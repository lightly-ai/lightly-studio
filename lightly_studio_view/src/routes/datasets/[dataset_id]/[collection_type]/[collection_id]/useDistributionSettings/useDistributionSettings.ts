import { writable, type Writable } from 'svelte/store';
import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
import type { DistributionViewSettings } from '$lib/components/DatasetDistributionPanel';

interface DistributionSettings {
    countMode: AnnotationCountMode;
    histogramBinCount: number;
    comparisonTagIds: string[];
    /** The source that the user picked, for example `classes` or `metadata`. */
    sourceId: string | undefined;
    /** The group that the user picked, for example a metadata key. */
    groupId: string | undefined;
    /** Sort, top N, orientation and value mode of the plots. Undefined until the panel opens. */
    viewSettings: DistributionViewSettings | undefined;
}

// The distribution panel unmounts when it closes, when another panel opens and when a sample
// opens. Its settings live here instead, per collection and in memory only, so they last for
// the session.
const settingsByCollection = new Map<string, Writable<DistributionSettings>>();

/** The distribution panel settings of a collection. */
export function useDistributionSettings(collectionId: string): Writable<DistributionSettings> {
    let settings = settingsByCollection.get(collectionId);
    if (!settings) {
        settings = writable({
            countMode: AnnotationCountMode.OBJECTS,
            histogramBinCount: 20,
            comparisonTagIds: [],
            sourceId: undefined,
            groupId: undefined,
            viewSettings: undefined
        });
        settingsByCollection.set(collectionId, settings);
    }
    return settings;
}
