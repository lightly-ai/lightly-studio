<script module>
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import PointCloudEndpointExample from './PointCloudEndpointExample.svelte';

    const queryClient = new QueryClient();
    const { Story } = defineMeta({
        title: 'Components/PointCloudEndpointExample',
        component: PointCloudEndpointExample,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' },
        argTypes: {
            datasetId: { control: 'text' },
            recordingId: { control: 'text' },
            channelId: { control: 'number' },
            timestampNs: { control: 'text' }
        },
        args: { datasetId: '', recordingId: '', channelId: 0, timestampNs: '' }
    });
</script>

<Story name="Load point cloud from API">
    {#snippet template(args)}
        <QueryClientProvider client={queryClient}>
            <div class="h-screen w-screen">
                <PointCloudEndpointExample {...args} />
            </div>
        </QueryClientProvider>
    {/snippet}
</Story>
