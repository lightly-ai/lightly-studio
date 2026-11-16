<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import WorkflowFileContextProbe from './WorkflowFileContextProbe.test.svelte';

    type Props = ComponentProps<typeof WorkflowFileContextProbe>;

    const { onContext }: Props = $props();

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
</script>

<QueryClientProvider {client}>
    <WorkflowFileContextProbe {onContext} />
</QueryClientProvider>
