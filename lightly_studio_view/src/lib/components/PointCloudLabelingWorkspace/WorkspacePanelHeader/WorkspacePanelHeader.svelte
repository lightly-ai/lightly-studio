<script lang="ts">
    import type { Snippet } from 'svelte';

    /** Inputs and callbacks for workspace panel header. */
    interface Props {
        /** Panel title displayed at the left of the header. */
        title: string;
        /** Optional actions aligned at the right of the panel header. */
        actions?: Snippet;
    }

    let { title, actions }: Props = $props();
</script>

<div class="flex shrink-0 items-center justify-between bg-background px-3 py-1 text-xs">
    <span class="text-muted-foreground">{title}</span>
    <div class="flex items-center gap-1">
        {@render actions?.()}
    </div>
</div>
