<script lang="ts">
    import type { Component } from 'svelte';

    interface Props {
        label: string;
        icon: Component;
        onclick: () => void;
    }

    let { label, icon: Icon, onclick }: Props = $props();
</script>

<button
    type="button"
    class="inline-flex h-6 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-border bg-muted/40 px-2 text-xs text-foreground/80 transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
    {onclick}
>
    <Icon class="size-3.5 shrink-0" aria-hidden="true" />
    {label}
</button>
