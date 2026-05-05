<script lang="ts">
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import SelectableBox from '../SelectableBox/SelectableBox.svelte';

    let { isSelected = false }: { isSelected?: boolean } = $props();

    const { user } = useAuth();

    const shouldRenderTag = $derived(isSelected && hasMinimumRole(user?.role, 'labeler'));
</script>

{#if shouldRenderTag}
    <div
        class="pointer-events-none absolute right-2 top-1.5 z-10"
        data-testid="grid-item-tag"
        inert
    >
        <SelectableBox onSelect={() => undefined} isSelected={true} />
    </div>
{/if}
