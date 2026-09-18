<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import type { CreateQueryResult } from '@tanstack/svelte-query';
    import type { McapSequenceSummary } from '$lib/api/lightly_studio_local/types.gen';
    import WorkspaceFilterBar from './WorkspaceFilterBar.svelte';

    function makeSummary(data: McapSequenceSummary): CreateQueryResult<McapSequenceSummary, Error> {
        return { data, status: 'success', isSuccess: true } as unknown as CreateQueryResult<
            McapSequenceSummary,
            Error
        >;
    }

    const baseSummary: McapSequenceSummary = {
        recording_id: 'rec-0001',
        format: 'mcap',
        start_log_time_ns: 1_700_000_000_000_000,
        lidar_channels: [
            {
                channel_id: 1,
                group_component_name: 'lidar_top',
                group_component_index: 0,
                frame_id: 'lidar_top'
            }
        ],
        camera_channels: [
            {
                channel_id: 2,
                group_component_name: 'front',
                group_component_index: 0,
                frame_id: 'front'
            },
            {
                channel_id: 3,
                group_component_name: 'rear',
                group_component_index: 1,
                frame_id: 'rear'
            },
            {
                channel_id: 4,
                group_component_name: 'left',
                group_component_index: 2,
                frame_id: null
            },
            {
                channel_id: 5,
                group_component_name: 'right',
                group_component_index: 3,
                frame_id: null
            }
        ]
    };

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/WorkspaceFilterBar',
        component: WorkspaceFilterBar,
        tags: ['autodocs']
    });
</script>

<Story name="No summary (loading)" args={{}} />

<Story name="One lidar, four cameras" args={{ summary: makeSummary(baseSummary) }} />

<Story
    name="Lidar only"
    args={{
        summary: makeSummary({
            ...baseSummary,
            camera_channels: []
        })
    }}
/>

<Story
    name="Cameras only"
    args={{
        summary: makeSummary({
            ...baseSummary,
            lidar_channels: []
        })
    }}
/>

<Story
    name="Empty channels"
    args={{
        summary: makeSummary({
            ...baseSummary,
            lidar_channels: [],
            camera_channels: []
        })
    }}
/>
