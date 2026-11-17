<script lang="ts">
    import { splitMatch } from '$lib/components/FilterList/filterList.helpers';
    import type { MatchRange } from './treeSearch';

    interface Props {
        text: string;
        range?: MatchRange | null;
    }

    let { text, range = null }: Props = $props();

    const [before, match, after] = $derived(splitMatch(text, range));
</script>

{before}{#if match}<mark class="rounded-sm bg-primary/25 text-foreground">{match}</mark>{/if}{after}
