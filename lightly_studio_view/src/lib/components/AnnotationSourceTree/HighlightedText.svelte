<script lang="ts">
    import { splitAtRange, type MatchRange } from './treeSearch';

    interface Props {
        text: string;
        range?: MatchRange | null;
    }

    let { text, range = null }: Props = $props();

    const parts = $derived(splitAtRange(text, range));
</script>

{parts.before}{#if parts.match}<mark class="rounded-sm bg-primary/25 text-foreground"
        >{parts.match}</mark
    >{/if}{parts.after}
