import { writable, type Writable } from 'svelte/store';
import type {
    ClassSetConfig,
    ColorConfig
} from '$lib/components/ConfusionMatrix/ClassSetDialog/types';

interface ConfusionMatrixSettings {
    config: ClassSetConfig;
    color: ColorConfig;
}

// The evaluations panel unmounts when it closes, when another panel opens and when a sample
// opens. Its state lives here instead, in memory only, so it lasts for the session.
const expandedRunByCollection = new Map<string, Writable<string | null>>();
const matrixSettingsByRun = new Map<string, Writable<ConfusionMatrixSettings | null>>();

const getOrCreate = <T>(map: Map<string, Writable<T>>, key: string, initial: T): Writable<T> => {
    let store = map.get(key);
    if (!store) {
        store = writable(initial);
        map.set(key, store);
    }
    return store;
};

/** The evaluation run open in the evaluations panel of a collection. Null shows the list. */
export function useExpandedEvaluationRun(collectionId: string): Writable<string | null> {
    return getOrCreate(expandedRunByCollection, collectionId, null);
}

/** The confusion matrix class and color settings of an evaluation run. Null until applied. */
export function useConfusionMatrixSettings(
    evaluationRunId: string
): Writable<ConfusionMatrixSettings | null> {
    return getOrCreate(matrixSettingsByRun, evaluationRunId, null);
}
