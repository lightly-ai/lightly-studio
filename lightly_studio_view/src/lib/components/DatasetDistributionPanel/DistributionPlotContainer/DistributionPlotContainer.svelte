<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Spinner } from '$lib/components';

    interface Props {
        loading: boolean;
        children: Snippet;
    }

    let { loading, children }: Props = $props();
</script>

<div class="relative flex min-h-0 flex-1 flex-col" aria-busy={loading}>
    <div class="flex min-h-0 flex-1 flex-col" inert={loading}>
        {@render children()}
    </div>
    {#if loading}
        <div
            class="absolute inset-0 z-10 flex items-center justify-center rounded-md bg-background/70"
            data-testid="distribution-plot-loading"
        >
            <Spinner size="large" />
        </div>
    {/if}
</div>
