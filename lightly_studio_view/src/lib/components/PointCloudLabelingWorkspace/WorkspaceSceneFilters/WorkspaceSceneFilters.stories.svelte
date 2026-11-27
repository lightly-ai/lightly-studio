<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import WorkspaceSceneFilters from './WorkspaceSceneFilters.svelte';

    const lidarChannels: ChannelSummaryView[] = [
        {
            channel_id: 1,
            group_component_name: 'lidar_top',
            group_component_index: 0,
            frame_id: 'lidar_top'
        }
    ];

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/WorkspaceSceneFilters',
        component: WorkspaceSceneFilters,
        tags: ['autodocs'],
        args: {
            referenceFrames: [],
            referenceFrameId: '',
            onSelectReferenceFrame: fn(),
            lidarChannels: [],
            selectedLidarChannels: [],
            colorMode: 'density',
            onColorModeChange: fn(),
            onToggleLidarChannel: fn(),
            onSetLidarChannels: fn()
        }
    });
</script>

<Story name="No channels (loading)" args={{}} />

<Story
    name="One lidar, two frames"
    args={{
        lidarChannels,
        selectedLidarChannels: [1],
        referenceFrames: [{ name: 'map' }, { name: 'CABIN' }],
        referenceFrameId: 'map'
    }}
/>

<Story name="Nothing selected" args={{ lidarChannels }} />
