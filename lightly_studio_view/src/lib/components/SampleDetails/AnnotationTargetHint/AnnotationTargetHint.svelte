<script lang="ts">
    import { useAnnotateVariant } from '$lib/hooks';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    // Variant "radio": asks for a source before the first annotation instead of a toast after.
    interface Props {
        /** Whether no source is picked yet. */
        needsPick: boolean;
    }

    let { needsPick }: Props = $props();

    const { annotateVariant } = useAnnotateVariant();
    const { isEditingMode } = useGlobalStorage();
</script>

{#if $annotateVariant === 'radio' && $isEditingMode && needsPick}
    <p class="mb-2 text-xs text-amber-400" data-testid="annotation-target-hint">
        Pick where new annotations go.
    </p>
{/if}
