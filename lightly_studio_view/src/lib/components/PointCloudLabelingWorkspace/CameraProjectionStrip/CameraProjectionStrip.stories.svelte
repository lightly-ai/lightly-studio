<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import CameraProjectionStrip from './CameraProjectionStrip.svelte';

    // No backend in Storybook: the frame queries never resolve, so each tile shows its placeholder.
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const cameraChannels = [
        'CAM_FRONT_LEFT',
        'CAM_FRONT',
        'CAM_FRONT_RIGHT',
        'CAM_BACK_LEFT',
        'CAM_BACK',
        'CAM_BACK_RIGHT'
    ].map((name, index) => ({
        channel_id: index + 1,
        group_component_name: name,
        group_component_index: index
    }));

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/CameraProjectionStrip',
        component: CameraProjectionStrip,
        parameters: { layout: 'fullscreen' },
        args: {
            datasetId: 'dataset',
            sequenceId: 'sequence',
            seqNumber: 0,
            cameraChannels,
            selectedChannelIds: cameraChannels.map(({ channel_id }) => channel_id),
            onHide: fn(),
            onDockChange: fn(),
            onToggleCameraChannel: fn(),
            onSetCameraChannels: fn()
        }
    });
</script>

<Story name="At the bottom" args={{ dock: 'bottom' }}>
    {#snippet template(args)}
        <QueryClientProvider client={queryClient}>
            <div class="h-48 w-full">
                <CameraProjectionStrip {...args} />
            </div>
        </QueryClientProvider>
    {/snippet}
</Story>

<Story name="On the right" args={{ dock: 'right' }}>
    {#snippet template(args)}
        <QueryClientProvider client={queryClient}>
            <div class="h-[32rem] w-72">
                <CameraProjectionStrip {...args} />
            </div>
        </QueryClientProvider>
    {/snippet}
</Story>
