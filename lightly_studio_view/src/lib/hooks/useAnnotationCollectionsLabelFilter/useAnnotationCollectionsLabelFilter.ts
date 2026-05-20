/**
 * Manages hierarchical annotation collection+label filter state.
 *
 * State is a singleton so it persists across grid → details navigation.
 * All collections and all their labels start selected (no filter applied).
 * When the user deselects anything, a per_collection_label_filters payload
 * is produced and sent to the backend.
 */
import { derived, get, readonly, writable } from 'svelte/store';
import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';

export interface LabelInfo {
    id: string;
    name: string;
}

export interface CollectionWithLabels {
    collectionId: string;
    name: string;
    labels: LabelInfo[];
    /** @deprecated use labels */
    labelIds?: string[];
}

// Singleton stores — survive route changes within the same SvelteKit session.
const selectedLabels = writable<Map<string, Set<string>>>(new Map());
const allAvailableLabels = writable<Map<string, string[]>>(new Map());
// Maps labelId → labelName for rendering checks (details view has name only, not id).
const labelIdToName = writable<Record<string, string>>({});
const collectionIdToName = writable<Record<string, string>>({});
const initialized = writable(false);

export const useAnnotationCollectionsLabelFilter = () => {
    /** Call once when the panel has loaded all collection+label data. */
    const initializeAll = (collections: CollectionWithLabels[]) => {
        if (get(initialized)) return;

        const ids = collections.map((c) => ({
            ...c,
            labelIds: c.labels.map((l) => l.id)
        }));

        const available = new Map(ids.map((c) => [c.collectionId, c.labelIds]));
        const selected = new Map(ids.map((c) => [c.collectionId, new Set(c.labelIds)]));
        const names = Object.fromEntries(ids.map((c) => [c.collectionId, c.name]));
        const idToName: Record<string, string> = {};
        for (const c of collections) {
            for (const l of c.labels) {
                idToName[l.id] = l.name;
            }
        }

        allAvailableLabels.set(available);
        selectedLabels.set(selected);
        collectionIdToName.set(names);
        labelIdToName.set(idToName);
        initialized.set(true);
    };

    /**
     * Toggle a whole collection. If all its labels are selected, deselect all.
     * If some or none are selected, select all.
     */
    const toggleCollection = (collectionId: string) => {
        selectedLabels.update((sel) => {
            const available = get(allAvailableLabels).get(collectionId) ?? [];
            const current = sel.get(collectionId) ?? new Set<string>();
            const next = new Map(sel);
            next.set(
                collectionId,
                current.size === available.length ? new Set() : new Set(available)
            );
            return next;
        });
    };

    const toggleLabel = (collectionId: string, labelId: string) => {
        selectedLabels.update((sel) => {
            const next = new Map(sel);
            const current = new Set(next.get(collectionId) ?? []);
            if (current.has(labelId)) {
                current.delete(labelId);
            } else {
                current.add(labelId);
            }
            next.set(collectionId, current);
            return next;
        });
    };

    /** 'all' | 'indeterminate' | 'none' for a given collection. */
    const getCollectionCheckState = (
        sel: Map<string, Set<string>>,
        avail: Map<string, string[]>,
        collectionId: string
    ): 'all' | 'indeterminate' | 'none' => {
        const selectedCount = sel.get(collectionId)?.size ?? 0;
        const availableCount = avail.get(collectionId)?.length ?? 0;
        if (availableCount === 0 || selectedCount === 0) return 'none';
        if (selectedCount === availableCount) return 'all';
        return 'indeterminate';
    };

    /**
     * Derived: undefined when all selected (no filtering), otherwise
     * an AnnotationsFilter with per_collection_label_filters.
     */
    const annotationFilter = derived(
        [selectedLabels, allAvailableLabels, initialized],
        ([$sel, $avail, $init]): AnnotationsFilter | undefined => {
            if (!$init) return undefined;

            // Check if everything is selected
            let allSelected = true;
            for (const [collectionId, labelIds] of $avail) {
                if (($sel.get(collectionId)?.size ?? 0) !== labelIds.length) {
                    allSelected = false;
                    break;
                }
            }
            if (allSelected) return undefined;

            const perCollectionFilters = Array.from($avail.entries())
                .map(([collectionId]) => {
                    const activeLabelIds = $sel.get(collectionId);
                    if (!activeLabelIds || activeLabelIds.size === 0) return null;
                    return {
                        collection_id: collectionId,
                        annotation_label_ids: Array.from(activeLabelIds)
                    };
                })
                .filter((f): f is NonNullable<typeof f> => f !== null);

            return {
                filter_type: 'annotations',
                per_collection_label_filters: perCollectionFilters
            };
        }
    );

    /** Collection IDs with at least one active label — used for color coding. */
    const selectedCollectionIds = derived(selectedLabels, ($sel) =>
        Array.from($sel.entries())
            .filter(([, ids]) => ids.size > 0)
            .map(([id]) => id)
    );

    /**
     * Maps collectionId → Set<labelName> for client-side rendering checks.
     * Use this when only label name is available (e.g. AnnotationView in details view).
     */
    const selectedLabelNames = derived([selectedLabels, labelIdToName], ([$sel, $idToName]) => {
        const result = new Map<string, Set<string>>();
        for (const [collectionId, labelIds] of $sel) {
            result.set(
                collectionId,
                new Set(
                    Array.from(labelIds)
                        .map((id) => $idToName[id])
                        .filter(Boolean)
                )
            );
        }
        return result;
    });

    const reset = () => {
        selectedLabels.set(new Map());
        allAvailableLabels.set(new Map());
        labelIdToName.set({});
        collectionIdToName.set({});
        initialized.set(false);
    };

    return {
        annotationFilter,
        selectedCollectionIds,
        selectedLabels: readonly(selectedLabels),
        selectedLabelNames,
        allAvailableLabels: readonly(allAvailableLabels),
        collectionIdToName: readonly(collectionIdToName),
        initialized: readonly(initialized),
        initializeAll,
        toggleCollection,
        toggleLabel,
        getCollectionCheckState,
        reset
    };
};
