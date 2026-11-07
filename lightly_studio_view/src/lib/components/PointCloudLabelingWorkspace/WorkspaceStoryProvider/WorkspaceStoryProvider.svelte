<script lang="ts">
    import { QueryClient, setQueryClientContext } from '@tanstack/svelte-query';
    import { onDestroy, type Snippet } from 'svelte';
    import { createWorkspaceController } from '$lib/components/PointCloudLabelingWorkspace/createWorkspaceController.svelte';
    import { providePointCloudWorkspaceLayoutContext } from '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte';
    import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

    interface Props {
        children: Snippet;
    }

    let { children }: Props = $props();
    const client = new QueryClient({
        defaultOptions: { queries: { enabled: false, retry: false, staleTime: Infinity } }
    });
    // The summary query enables itself; seed it while empty IDs disable tick and cloud queries.
    client.setQueryData(getSummaryOptions({ path: { dataset_id: '', sequence_id: '' } }).queryKey, {
        recording_id: '',
        file_name: 'story.mcap',
        format: 'mcap',
        start_log_time_ns: null,
        lidar_channels: [],
        camera_channels: [],
        reference_frames: []
    });
    setQueryClientContext(client);
    const controller = createWorkspaceController(() => ({
        datasetId: '',
        sequenceId: ''
    }));
    providePointCloudWorkspaceLayoutContext(controller.getLayout, controller);
    onDestroy(() => client.clear());
</script>

{@render children()}
