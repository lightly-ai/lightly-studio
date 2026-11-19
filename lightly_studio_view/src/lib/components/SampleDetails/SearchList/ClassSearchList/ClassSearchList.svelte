<script lang="ts">
    import SearchList from '../SearchList.svelte';
    import { matchClasses } from '../searchRanking';

    interface Props {
        names: string[];
        /** Recent classes, listed first within a match tier. */
        recent: string[];
        /** The class of the annotation being relabeled, listed and highlighted first. */
        current?: string;
        showBackHint?: boolean;
        /** Gets an existing class or the name of a class to create. */
        onPick: (className: string) => void;
        onCancel: () => void;
    }

    const { names, recent, current, showBackHint, onPick, onCancel }: Props = $props();
    let query = $state('');

    const rows = $derived.by(() => {
        const { matches, createName } = matchClasses({ names, recent, current, query });
        const classRows = matches.map((name) => ({
            value: `class:${name}`,
            label: name,
            onPick: () => onPick(name)
        }));
        if (createName === null) return classRows;
        const createRow = {
            value: 'create',
            label: createName,
            isCreate: true,
            onPick: () => onPick(createName)
        };
        return [...classRows, createRow];
    });
</script>

<SearchList
    {rows}
    bind:query
    label="Annotation class"
    placeholder="Pick a class"
    {showBackHint}
    {onCancel}
/>
