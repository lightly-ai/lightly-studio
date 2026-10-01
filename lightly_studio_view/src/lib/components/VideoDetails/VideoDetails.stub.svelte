<script lang="ts" module>
    /** Props seen by any stubbed child, in render order. */
    export const capturedProps: Array<Record<string, unknown>> = [];

    export function resetCapturedProps(): void {
        capturedProps.length = 0;
    }
</script>

<script lang="ts">
    import type { Snippet } from 'svelte';

    // `videoEl` is declared bindable so `bind:videoEl` on the VideoPlayer stub works.
    // This is a test-only stub, never compiled as a custom element, and the
    // `...rest` capture is intentional — suppress the custom-element props warning.
    // svelte-ignore custom_element_props_identifier
    let {
        videoEl = $bindable(null),
        children,
        ...rest
    }: { videoEl?: unknown; children?: Snippet; [key: string]: unknown } = $props();

    $effect(() => {
        capturedProps.push({ ...rest });
    });
</script>

{@render children?.()}
