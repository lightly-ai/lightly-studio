<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        title: string;
        children: Snippet;
        // Shown below a divider, e.g. the class select and the save buttons.
        saveControls?: Snippet;
    }

    let { title, children, saveControls }: Props = $props();
</script>

<div class="absolute bottom-11 w-[min(90vw,265px)]">
    <div
        class="pointer-events-auto grid max-h-[70vh] gap-1.5 overflow-y-auto rounded-lg bg-muted p-2 shadow-md"
        role="dialog"
        aria-label={title}
    >
        <div class="truncate text-sm font-semibold text-foreground">
            {title}
        </div>

        {@render children()}

        {#if saveControls}
            <div class="h-px bg-border"></div>
            {@render saveControls()}
        {/if}
    </div>
</div>
