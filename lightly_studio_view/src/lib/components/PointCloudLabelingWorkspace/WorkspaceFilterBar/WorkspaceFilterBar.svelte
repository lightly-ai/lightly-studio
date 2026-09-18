<script lang="ts">
    import { Select, type SelectItem } from '$lib/components/Select';
    import type { CreateQueryResult } from '@tanstack/svelte-query';
    import type { McapSequenceSummary } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        summary?: CreateQueryResult<McapSequenceSummary, Error>;
    }

    let { summary }: Props = $props();

    const lidarItems = $derived<SelectItem[]>(
        summary?.data?.lidar_channels.map((c) => ({
            value: c.group_component_name,
            label: c.group_component_name
        })) ?? []
    );

    const cameraItems = $derived<SelectItem[]>(
        summary?.data?.camera_channels.map((c) => ({
            value: c.group_component_name,
            label: c.group_component_name
        })) ?? []
    );

    let selectedLidar = $state<string | undefined>(undefined);
    let selectedCamera = $state<string | undefined>(undefined);
</script>

<div
    class="flex shrink-0 items-center gap-4 border-b bg-background px-4 py-2"
    data-testid="workspace-filter-bar"
>
    <Select
        items={lidarItems}
        bind:value={selectedLidar}
        placeholder="Lidar"
        disabled={lidarItems.length === 0}
        class="w-64"
        testId="workspace-lidar-select"
    />
    <Select
        items={cameraItems}
        bind:value={selectedCamera}
        placeholder="Camera"
        disabled={cameraItems.length === 0}
        class="w-64"
        testId="workspace-camera-select"
    />
</div>
