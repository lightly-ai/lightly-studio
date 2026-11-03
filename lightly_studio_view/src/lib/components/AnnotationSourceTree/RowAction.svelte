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
    class="shrink-0 rounded px-1 text-xs text-muted-foreground opacity-0 hover:bg-background hover:text-foreground focus:opacity-100 group-hover:opacity-100"
    {onclick}>{label}</button
>
