<script lang="ts">
    import Layout from './+layout.svelte';
    import type { LayoutLoadResult } from './+layout';

    interface Props {
        data: LayoutLoadResult;
    }

    let { data }: Props = $props();
</script>

<Layout {data}>
    {#snippet children()}
        <div data-testid="layout-test-child">workspace-child</div>
    {/snippet}
</Layout>
