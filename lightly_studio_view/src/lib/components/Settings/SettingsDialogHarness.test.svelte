<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import SettingsDialog from './SettingsDialog.svelte';

    interface Props {
        client: QueryClient;
    }
    let { client }: Props = $props();
</script>

<QueryClientProvider {client}>
    <SettingsDialog />
</QueryClientProvider>
