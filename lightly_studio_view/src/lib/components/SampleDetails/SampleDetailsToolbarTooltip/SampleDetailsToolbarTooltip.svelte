<script lang="ts">
    import type { Snippet } from 'svelte';

    const {
        label,
        shortcut,
        action,
        hint,
        children
    }: {
        label: string;
        shortcut?: string;
        action?: string;
        hint?: string;
        children: Snippet;
    } = $props();
    let visible = $state(false);
</script>

<div
    class="relative"
    onpointerenter={() => (visible = true)}
    onpointerleave={() => (visible = false)}
    onpointerdown={() => (visible = false)}
>
    {@render children()}

    {#if visible}
        <div
            class="
        pointer-events-none
        absolute left-full top-1/2 z-50 ml-3
        -translate-y-1/2
      "
        >
            <div
                class="
          flex
          flex-col
          gap-0.5 whitespace-nowrap
          rounded-lg border
          border-white/10 bg-black
          px-3
          py-2
          text-xs text-white shadow-lg
        "
            >
                <span class="font-medium">{label}</span>
                {#if shortcut && action}
                    <span class="text-white/70"
                        >Press <kbd class="rounded border border-white/10 bg-white/10 px-1"
                            >{shortcut}</kbd
                        >
                        to {action}</span
                    >
                {/if}
                {#if hint}
                    <span class="text-white/50">{hint}</span>
                {/if}
            </div>
        </div>
    {/if}
</div>
