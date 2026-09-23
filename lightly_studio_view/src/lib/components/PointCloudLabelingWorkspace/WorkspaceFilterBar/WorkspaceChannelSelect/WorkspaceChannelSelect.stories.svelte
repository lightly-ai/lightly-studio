<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import WorkspaceChannelSelect from './WorkspaceChannelSelect.svelte';

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
        title: 'Components/PointCloudLabelingWorkspace/WorkspaceChannelSelect',
        component: WorkspaceChannelSelect,
        tags: ['autodocs'],
        args: {
            label: 'Camera',
            channels: cameraChannels,
            selectedChannels: [],
            onToggleChannel: fn(),
            testId: 'workspace-camera-select'
        }
    });
</script>

<Story name="Nothing selected" args={{}} />

<Story name="One selected" args={{ selectedChannels: [2] }} />

<Story name="Several selected" args={{ selectedChannels: [2, 4] }} />

<Story name="No channels (disabled)" args={{ channels: [] }} />
