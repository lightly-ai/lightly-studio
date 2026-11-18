<script lang="ts">
    import { PICK_SOURCE_MESSAGE } from '$lib/hooks';

    // Asks for a source before the first annotation instead of a toast after. Render it only
    // where the target can be picked.
    interface Props {
        /** Whether no source is picked yet. */
        needsPick: boolean;
    }

    let { needsPick }: Props = $props();
</script>

{#if needsPick}
    <p class="mb-2 text-xs text-amber-400" data-testid="annotation-target-hint">
        {PICK_SOURCE_MESSAGE}
    </p>
{/if}
