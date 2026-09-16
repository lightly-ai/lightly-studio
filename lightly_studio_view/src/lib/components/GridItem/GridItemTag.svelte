<script lang="ts">
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import SelectableBox from '../SelectableBox/SelectableBox.svelte';

    let {
        isSelected = false,
        onSelect
    }: {
        isSelected?: boolean;
        /**
         * Makes the box the selection control. Without it the box is decorative and the tile
         * itself owns selection, which is how the annotation, video and frame grids work.
         */
        onSelect?: (event: MouseEvent) => void;
    } = $props();

    const { user } = useAuth();

    const shouldRenderTag = $derived(hasMinimumRole(user?.role, 'labeler'));

    // The click is read rather than SelectableBox's boolean callback because range selection
    // needs the original event's shiftKey.
    function handleClick(event: MouseEvent) {
        if (!onSelect) return;
        event.stopPropagation();
        onSelect(event);
    }
</script>

{#if shouldRenderTag}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="absolute right-2 top-1.5 z-10"
        class:pointer-events-none={!onSelect}
        data-testid="grid-item-tag"
        data-grid-item-no-drag={onSelect ? '' : undefined}
        inert={!onSelect}
        onclick={handleClick}
    >
        <SelectableBox onSelect={() => undefined} {isSelected} />
    </div>
{/if}
