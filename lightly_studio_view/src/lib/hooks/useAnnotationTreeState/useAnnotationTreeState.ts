import { derived, type Readable } from 'svelte/store';
import type { GroupBy } from '$lib/components/AnnotationTree/groupPairRows';
import type { PairKey } from '$lib/components/AnnotationTree/pairRows';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

const STORAGE_KEY = 'lightlyStudio_annotation_tree';

type TreeState = {
    untickedPairs: PairKey[];
    untickedUnannotated: string[];
    hiddenPairs: PairKey[];
    groupBy: GroupBy;
    // A missing group id means the default state, which depends on the group count.
    openGroups: Record<string, boolean>;
};

const createEmptyState = (): TreeState => ({
    untickedPairs: [],
    untickedUnannotated: [],
    hiddenPairs: [],
    groupBy: 'source',
    openGroups: {}
});

const statesStore = useSessionStorage<Record<string, TreeState>>(STORAGE_KEY, {});

const readState = (states: unknown, collectionId: string): TreeState => {
    const isRecord = (value: unknown): value is Record<string, unknown> =>
        typeof value === 'object' && value !== null && !Array.isArray(value);
    const entry = isRecord(states) ? states[collectionId] : undefined;
    return { ...createEmptyState(), ...(isRecord(entry) ? entry : {}) };
};

const isSamePair = (a: PairKey, b: PairKey) =>
    a.collection_id === b.collection_id && a.annotation_label_id === b.annotation_label_id;

const withPairs = (list: PairKey[], pairs: PairKey[], present: boolean): PairKey[] => {
    const rest = list.filter((item) => !pairs.some((pair) => isSamePair(item, pair)));
    if (!present) return rest;
    const added = pairs.filter(
        (pair, index) => pairs.findIndex((other) => isSamePair(other, pair)) === index
    );
    return [...rest, ...added];
};

const withIds = (list: string[], ids: string[], present: boolean): string[] => {
    const rest = list.filter((id) => !ids.includes(id));
    return present ? [...rest, ...new Set(ids)] : rest;
};

/**
 * The key of the tree state of a grid tab. The Images grid keeps it under its collection, and
 * the Annotations grid under its annotation source, so each tab has its own ticks and eyes.
 */
export const treeStateKey = (collectionId: string, sourceId?: string) => sourceId ?? collectionId;

export function useAnnotationTreeState(collectionId: string) {
    const select = <K extends keyof TreeState>(key: K): Readable<TreeState[K]> =>
        derived(statesStore, ($states) => readState($states, collectionId)[key]);

    const update = (change: (state: TreeState) => Partial<TreeState>) =>
        statesStore.update((states) => {
            const state = readState(states, collectionId);
            const base = typeof states === 'object' && states !== null ? states : {};
            return { ...base, [collectionId]: { ...state, ...change(state) } };
        });

    const setTicked = (pairs: PairKey[], ticked: boolean) =>
        update((state) => ({ untickedPairs: withPairs(state.untickedPairs, pairs, !ticked) }));

    const setUnannotatedTicked = (sourceIds: string[], ticked: boolean) =>
        update((state) => ({
            untickedUnannotated: withIds(state.untickedUnannotated, sourceIds, !ticked)
        }));

    const setVisible = (pairs: PairKey[], visible: boolean) =>
        update((state) => ({ hiddenPairs: withPairs(state.hiddenPairs, pairs, !visible) }));

    const only = (pairs: PairKey[], allPairs: PairKey[]) =>
        update((state) => {
            const others = allPairs.filter((pair) => !pairs.some((kept) => isSamePair(kept, pair)));
            return {
                untickedPairs: withPairs(withPairs(state.untickedPairs, pairs, false), others, true)
            };
        });

    const setGroupBy = (groupBy: GroupBy) => update(() => ({ groupBy }));

    const toggleOpen = (groupId: string, currentlyOpen = true) =>
        update((state) => ({
            openGroups: {
                ...state.openGroups,
                [groupId]: !(state.openGroups[groupId] ?? currentlyOpen)
            }
        }));

    const resetTicks = () => update(() => ({ untickedPairs: [], untickedUnannotated: [] }));

    const dropSource = (sourceId: string) =>
        update((state) => {
            const openGroups = { ...state.openGroups };
            delete openGroups[sourceId];
            return {
                untickedPairs: state.untickedPairs.filter(
                    (pair) => pair.collection_id !== sourceId
                ),
                hiddenPairs: state.hiddenPairs.filter((pair) => pair.collection_id !== sourceId),
                untickedUnannotated: state.untickedUnannotated.filter((id) => id !== sourceId),
                openGroups
            };
        });

    return {
        untickedPairs: select('untickedPairs'),
        untickedUnannotated: select('untickedUnannotated'),
        hiddenPairs: select('hiddenPairs'),
        groupBy: select('groupBy'),
        openGroups: select('openGroups'),
        setTicked,
        setUnannotatedTicked,
        setVisible,
        only,
        setGroupBy,
        toggleOpen,
        resetTicks,
        dropSource
    };
}
