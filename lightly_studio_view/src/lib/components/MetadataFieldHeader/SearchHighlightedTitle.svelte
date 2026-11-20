<script lang="ts">
    import { highlightRange, splitMatch } from '$lib/components/FilterList';
    import { getFieldSearchContext } from './fieldSearchContext';

    interface Props {
        title: string;
    }

    const { title }: Props = $props();

    const getSearch = getFieldSearchContext();
    const [before, match, after] = $derived(splitMatch(title, highlightRange(title, getSearch())));
</script>

<span class="truncate"
    >{before}{#if match}<mark class="rounded-sm bg-primary/25 text-foreground">{match}</mark
        >{/if}{after}</span
>
