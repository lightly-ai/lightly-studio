<script lang="ts">
    interface Props {
        label: string;
        ariaLabel: string;
        onclick: () => void;
    }

    let { label, ariaLabel, onclick }: Props = $props();
</script>

<button
    type="button"
    aria-label={ariaLabel}
    class="hidden shrink-0 rounded px-1 text-xs text-muted-foreground hover:bg-background hover:text-foreground focus:inline-block group-focus-within:inline-block group-hover:inline-block"
    {onclick}>{label}</button
>
