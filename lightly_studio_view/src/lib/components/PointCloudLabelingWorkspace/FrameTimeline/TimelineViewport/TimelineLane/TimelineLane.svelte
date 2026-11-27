<script lang="ts">
    import type { Snippet } from 'svelte';

    /**
     * Places timeline content inside the shared horizontal scroll area.
     */
    interface Props {
        children: Snippet;
        /** Positions the lane; it must be positioned and sized by the caller. */
        class?: string;
    }

    let { children, class: className = '' }: Props = $props();
</script>

<div class="relative w-full {className}">
    {@render children()}
</div>
