<script lang="ts">
    import { QueryClientProvider } from '@tanstack/svelte-query';

    let { children, queryClient } = $props();
</script>

<QueryClientProvider client={queryClient}>
    {@render children()}
</QueryClientProvider>
