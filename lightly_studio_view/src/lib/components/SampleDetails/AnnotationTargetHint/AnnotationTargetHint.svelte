<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    // Asks for a source before the first annotation instead of a toast after.
    interface Props {
        /** Whether no source is picked yet. */
        needsPick: boolean;
    }

    let { needsPick }: Props = $props();

    const { isEditingMode } = useGlobalStorage();
</script>

{#if $isEditingMode && needsPick}
    <p class="mb-2 text-xs text-amber-400" data-testid="annotation-target-hint">
        Pick where new annotations go.
    </p>
{/if}
