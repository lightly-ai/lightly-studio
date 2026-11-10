<script lang="ts">
    import { LOADING_SOURCES_MESSAGE, useAnnotationCollections } from '$lib/hooks';
    import SearchList from '../SearchList.svelte';
    import { listSourceRows } from './listSourceRows';

    // Mount it only while it is shown, for example in a popover: it loads the sources.
    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        /** A source to leave out, for example the one the annotation is in. */
        excludeSourceId?: string;
        /** Sources listed but not pickable, with the note that says why. */
        disabledSources?: { names: string[]; note: string };
        /** Whether a typed name that matches no source can be picked, to create that source. */
        allowCreate?: boolean;
        heading?: string;
        showBackHint?: boolean;
        disabled?: boolean;
        /** Gets an existing source or the name of a source to create. */
        onPick: (sourceName: string) => void;
        onCancel: () => void;
    }

    const {
        collectionId,
        excludeSourceId,
        disabledSources,
        allowCreate = false,
        heading,
        showBackHint,
        disabled,
        onPick,
        onCancel
    }: Props = $props();
    const sources = useAnnotationCollections(() => ({ collectionId }));
    let query = $state('');

    const rows = $derived(
        listSourceRows({
            sources: sources.data,
            query,
            excludeSourceId,
            disabledSources,
            allowCreate,
            onPick
        })
    );
</script>

<SearchList
    {rows}
    bind:query
    label="Annotation source"
    placeholder={allowCreate ? 'Search or create a source' : 'Pick a source'}
    {heading}
    loadingMessage={sources.isPending ? LOADING_SOURCES_MESSAGE : undefined}
    emptyMessage="No annotation source matches"
    {showBackHint}
    {disabled}
    {onCancel}
/>
