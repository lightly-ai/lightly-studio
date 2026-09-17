<script lang="ts">
    import { Search } from '@lucide/svelte';
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
    class="flex h-11 shrink-0 items-center gap-2 border-b bg-background px-3"
    data-testid="workspace-filter-bar"
>
    <div class="relative w-56 shrink-0">
        <Search
            class="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
        />
        <input
            type="text"
            disabled
            placeholder="Filter annotations…"
            aria-label="Filter annotations"
            class="h-8 w-full rounded-md border bg-muted/40 pl-8 pr-2 text-sm placeholder:text-muted-foreground disabled:cursor-not-allowed"
        />
    </div>
    <div class="flex min-w-0 items-center gap-1">
        <Select
            items={lidarItems}
            bind:value={selectedLidar}
            placeholder="Lidar"
            disabled={lidarItems.length === 0}
            size="xs"
            class="h-8 shrink-0 text-xs"
            testId="workspace-lidar-select"
        />
        <Select
            items={cameraItems}
            bind:value={selectedCamera}
            placeholder="Camera"
            disabled={cameraItems.length === 0}
            size="xs"
            class="h-8 shrink-0 text-xs"
            testId="workspace-camera-select"
        />
    </div>
</div>
