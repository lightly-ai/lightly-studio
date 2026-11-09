<script lang="ts">
    interface Props {
        target: string;
        onclick: () => void;
    }

    let { target, onclick }: Props = $props();
</script>

<button
    type="button"
    aria-label="Only {target}"
    class="hidden shrink-0 rounded px-1 text-xs text-muted-foreground hover:bg-background hover:text-foreground focus:inline-block group-focus-within:inline-block group-hover:inline-block"
    {onclick}>Only</button
>
