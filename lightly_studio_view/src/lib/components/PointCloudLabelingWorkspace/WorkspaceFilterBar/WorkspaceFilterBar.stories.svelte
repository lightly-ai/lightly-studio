<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import WorkspaceFilterBar from './WorkspaceFilterBar.svelte';

    const lidarChannels: ChannelSummaryView[] = [
        {
            channel_id: 1,
            group_component_name: 'lidar_top',
            group_component_index: 0,
            frame_id: 'lidar_top'
        }
    ];

    const cameraChannels: ChannelSummaryView[] = [
        {
            channel_id: 2,
            group_component_name: 'front',
            group_component_index: 0,
            frame_id: 'front'
        },
        { channel_id: 3, group_component_name: 'rear', group_component_index: 1, frame_id: 'rear' },
        { channel_id: 4, group_component_name: 'left', group_component_index: 2, frame_id: null },
        { channel_id: 5, group_component_name: 'right', group_component_index: 3, frame_id: null }
    ];

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/WorkspaceFilterBar',
        component: WorkspaceFilterBar,
        tags: ['autodocs'],
        args: {
            lidarChannels: [],
            cameraChannels: [],
            selectedLidarChannels: [],
            selectedCameraChannels: [],
            onToggleLidarChannel: fn(),
            onToggleCameraChannel: fn()
        }
    });
</script>

<Story name="No channels (loading)" args={{}} />

<Story
    name="One lidar, four cameras"
    args={{
        lidarChannels,
        cameraChannels,
        selectedLidarChannels: [1],
        selectedCameraChannels: [2, 4]
    }}
/>

<Story name="Lidar only" args={{ lidarChannels, selectedLidarChannels: [1] }} />

<Story name="Cameras only" args={{ cameraChannels, selectedCameraChannels: [2] }} />

<Story name="Nothing selected" args={{ lidarChannels, cameraChannels }} />
