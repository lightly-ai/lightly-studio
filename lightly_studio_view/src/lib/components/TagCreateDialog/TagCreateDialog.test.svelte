<script lang="ts">
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';

    import TagCreateDialog, { type UseTagsCreateDialog } from './TagCreateDialog.svelte';

    let {
        queryClient,
        TagCreateDialogProps
    }: { queryClient: QueryClient; TagCreateDialogProps: UseTagsCreateDialog } = $props();
</script>

<QueryClientProvider client={queryClient}>
    <TagCreateDialog {...TagCreateDialogProps} />
</QueryClientProvider>
