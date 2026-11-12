<script lang="ts">
    import { keepFocusOnMove } from './keepFocusOnMove.svelte';

    let {
        order,
        blurOnChange = false,
        resetScrollOnChange = false
    }: { order: string[]; blurOnChange?: boolean; resetScrollOnChange?: boolean } = $props();
    let container = $state<HTMLElement>();

    keepFocusOnMove(
        () => container,
        () => order
    );

    // Simulates the browser dropping focus and inner scroll when a node is moved.
    $effect.pre(() => {
        order.join();
        if (blurOnChange && document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }
        if (resetScrollOnChange) {
            container?.querySelectorAll<HTMLElement>('[data-inner]').forEach((inner) => {
                inner.scrollTop = 0;
            });
        }
    });
</script>

<div data-testid="scroller" style="overflow-y: auto">
    <div bind:this={container}>
        {#each order as id (id)}
            <div data-field-id={id}>
                <div data-inner data-testid="inner-{id}" style="overflow-y: auto">
                    <button>{id}</button>
                </div>
            </div>
        {/each}
    </div>
</div>
<button>outside</button>
