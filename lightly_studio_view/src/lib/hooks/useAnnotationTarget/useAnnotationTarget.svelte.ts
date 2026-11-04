import { untrack } from 'svelte';
import { fromStore, get } from 'svelte/store';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useDefaultSource } from '$lib/hooks/useDefaultSource/useDefaultSource';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSetTargetSource } from './useSetTargetSource';
import {
    getTargetBlockedReason,
    pickInitialSource,
    resolveTargetSource
} from './resolveTargetSource';

/**
 * The annotation source new annotations are written to, and the action that changes it.
 * Keeps `annotationSourceBlockedReason` in the shared context up to date, so drawing tools refuse
 * to create an annotation while no source is picked or the picked one is hidden. Call it from
 * one always-mounted component of the sample details page.
 */
export const useAnnotationTarget = ({
    getCollectionId,
    getIsTargetHidden
}: {
    getCollectionId: () => string;
    getIsTargetHidden: () => boolean;
}) => {
    const { context, setAnnotationSource } = useAnnotationLabelContext();
    const { lastAnnotationSource } = useGlobalStorage();
    const { defaultSources } = useDefaultSource();
    const defaultSourcesState = fromStore(defaultSources);
    const annotationCollections = useAnnotationCollections(() => ({
        collectionId: getCollectionId()
    }));

    const sourceNames = $derived(annotationCollections.data?.map((c) => c.name) ?? []);
    const targetSource = $derived(resolveTargetSource(context.annotationSource, sourceNames));

    $effect(() => {
        context.annotationSourceBlockedReason = getTargetBlockedReason(
            targetSource,
            getIsTargetHidden()
        );
    });

    // Seed the context with the default or the only source once the list has loaded, also when
    // Settings sets a default later. It does not write `lastAnnotationSource`, so a default never
    // looks like a remembered pick.
    $effect(() => {
        const initial = pickInitialSource({
            chosenSource: context.annotationSource,
            sourceNames,
            defaultSource: defaultSourcesState.current[getCollectionId()]
        });
        if (initial) setAnnotationSource(initial);
    });

    // A seeded default is not a pick, so it follows when Settings renames or replaces the default.
    $effect(() => {
        let previous: string | undefined;
        return defaultSources.subscribe((stored) => {
            const collectionId = untrack(getCollectionId);
            const next = stored[collectionId];
            const isSeeded =
                untrack(() => context.annotationSource) === previous &&
                get(lastAnnotationSource)[collectionId] !== previous;
            if (previous && next && isSeeded) setAnnotationSource(next);
            previous = next;
        });
    });

    // Settings can rename the target source while this page is open. The rename updates the
    // stored source, so follow it.
    $effect(() =>
        lastAnnotationSource.subscribe((stored) => {
            const name = stored[untrack(getCollectionId)];
            if (name && name !== untrack(() => context.annotationSource)) {
                setAnnotationSource(name);
            }
        })
    );

    const setTargetSource = useSetTargetSource(getCollectionId);

    return {
        get targetSource() {
            return targetSource;
        },
        setTargetSource
    };
};
