<script lang="ts">
    import { ChevronLeft, ChevronRight, Play } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { CreateQueryResult } from '@tanstack/svelte-query';
    import type { McapSequenceSummary } from '$lib/api/lightly_studio_local/types.gen';

    /**
     * Frame navigation, object tracks and keyframes for the active recording. Placeholder ruler
     * and lanes until frame loading lands; controls are disabled rather than wired to no-ops.
     */
    interface Props {
        summary?: CreateQueryResult<McapSequenceSummary, Error>;
    }

    let { summary }: Props = $props();

    const ticks = Array.from({ length: 24 }, (_, index) => index);
    const lanes = $derived(
        summary?.data
            ? [
                  ...summary.data.lidar_channels.map((c) => c.group_component_name),
                  ...summary.data.camera_channels.map((c) => c.group_component_name)
              ]
            : ['Track 1', 'Track 2']
    );
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-frame-timeline"
>
    <div class="flex shrink-0 items-center gap-1 border-b px-2 py-1">
        <Button
            variant="ghost"
            icon={ChevronLeft}
            ariaLabel="Previous frame"
            buttonProps={{ disabled: true, size: 'sm', class: 'h-7 w-7 p-0' }}
        />
        <Button
            variant="ghost"
            icon={Play}
            ariaLabel="Play frames"
            buttonProps={{ disabled: true, size: 'sm', class: 'h-7 w-7 p-0' }}
        />
        <Button
            variant="ghost"
            icon={ChevronRight}
            ariaLabel="Next frame"
            buttonProps={{ disabled: true, size: 'sm', class: 'h-7 w-7 p-0' }}
        />
        <span class="ml-2 text-xs text-muted-foreground">Frame — / —</span>
    </div>
    <div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-2 py-1.5">
        <div class="flex h-4 shrink-0 items-end gap-px" aria-hidden="true">
            {#each ticks as tick (tick)}
                <span class="w-full bg-border {tick % 5 === 0 ? 'h-3' : 'h-1.5'}"></span>
            {/each}
        </div>
        {#each lanes as lane (lane)}
            <div class="flex items-center gap-2">
                <span class="w-24 shrink-0 truncate text-xs text-muted-foreground">{lane}</span>
                <div class="h-4 flex-1 rounded bg-muted/50"></div>
            </div>
        {/each}
    </div>
</div>
