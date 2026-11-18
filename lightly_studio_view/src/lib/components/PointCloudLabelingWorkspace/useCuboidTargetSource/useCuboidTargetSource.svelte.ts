import { untrack } from 'svelte';
import { fromStore, get } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks';
import {
    isCuboidPickRemoved,
    resolveCuboidTargetSource,
    type CuboidTarget
} from './resolveCuboidTargetSource';

interface UseCuboidTargetSourceParams {
    /** The collection that holds the annotation sources of the sequence. */
    getCollectionId: () => string | undefined;
    /** The names of the annotation sources, undefined until they have loaded. */
    getSourceNames: () => string[] | undefined;
    /** Whether the source list failed to load. */
    getIsError: () => boolean;
}

export interface CuboidTargetSourceState extends CuboidTarget {
    /** A name typed on this page whose source is not created yet. */
    readonly typedSource: string | null;
    /** Picks the source new cuboids go to. Pass `isNew` for a typed name of a new source. */
    setTarget: (name: string, options?: { isNew?: boolean }) => void;
}

/**
 * Tracks the annotation source that new cuboids go to. The pick is remembered per collection.
 * Create it once per workspace.
 */
export function useCuboidTargetSource(
    params: UseCuboidTargetSourceParams
): CuboidTargetSourceState {
    const { lastAnnotationSource, updateLastAnnotationSource } = useGlobalStorage();
    const picks = fromStore(lastAnnotationSource);
    let typed = $state<{ collectionId: string; name: string } | null>(null);

    const typedSource = $derived(
        typed && typed.collectionId === params.getCollectionId() ? typed.name : null
    );
    const pick = $derived.by(() => {
        const collectionId = params.getCollectionId();
        return collectionId ? picks.current[collectionId] : undefined;
    });
    const target = $derived(
        resolveCuboidTargetSource({
            pick,
            typedSource,
            sourceNames: params.getSourceNames(),
            isError: params.getIsError()
        })
    );

    forgetRemovedPick(params.getCollectionId, params.getSourceNames);

    // A typed source is exempt from the list check only until the list contains it. After that,
    // a rename or delete must make the pick invalid like for any other source.
    $effect(() => {
        if (typedSource && params.getSourceNames()?.includes(typedSource)) typed = null;
    });

    function setTarget(name: string, options?: { isNew?: boolean }) {
        const trimmed = name.trim();
        const collectionId = params.getCollectionId();
        if (!trimmed || !collectionId) return;
        if (options?.isNew) typed = { collectionId, name: trimmed };
        updateLastAnnotationSource(collectionId, trimmed);
    }

    return {
        get targetSource() {
            return target.targetSource;
        },
        get blockedReason() {
            return target.blockedReason;
        },
        get needsPick() {
            return target.needsPick;
        },
        get typedSource() {
            return typedSource;
        },
        setTarget
    };
}

// Another tab or the Python API can rename or delete the picked source. The pick is then
// forgotten, so the next cuboid asks for a source instead of re-creating the old one.
function forgetRemovedPick(
    getCollectionId: () => string | undefined,
    getSourceNames: () => string[] | undefined
) {
    const { lastAnnotationSource, removeLastAnnotationSource } = useGlobalStorage();
    // Not reactive on purpose: it must not re-run the effect.
    let previous: { collectionId: string; names: string[] } | undefined;
    $effect(() => {
        const names = getSourceNames();
        const collectionId = getCollectionId();
        if (!names || !collectionId) return;
        untrack(() => {
            if (previous?.collectionId !== collectionId) return;
            const pick = get(lastAnnotationSource)[collectionId];
            const previousNames = previous.names;
            if (pick && isCuboidPickRemoved({ pick, previousNames, nextNames: names })) {
                removeLastAnnotationSource(collectionId, pick);
            }
        });
        previous = { collectionId, names };
    });
}
